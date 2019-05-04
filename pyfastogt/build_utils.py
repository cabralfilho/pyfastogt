import os
import stat
import re
import shutil
import subprocess
from pyfastogt import system_info, utils


class BuildSystem:
    def __init__(self, name: str, cmd_line: list, cmake_generator_arg: str):
        self.name_ = name
        self.cmd_line_ = cmd_line
        self.cmake_generator_arg_ = cmake_generator_arg

    def cmake_generator_arg(self) -> str:
        return self.cmake_generator_arg_

    def name(self) -> str:
        return self.name_

    def cmd_line(self) -> list:  # cmd + args
        return self.cmd_line_


SUPPORTED_BUILD_SYSTEMS = [BuildSystem('ninja', ['ninja'], 'Ninja'),
                           BuildSystem('make', ['make', '-j4'], 'Unix Makefiles'),
                           BuildSystem('gmake', ['gmake', '-j4'], 'Unix Makefiles')]


def get_supported_build_system_by_name(name) -> BuildSystem:
    return next((x for x in SUPPORTED_BUILD_SYSTEMS if x.name() == name), None)


class BuildError(Exception):
    def __init__(self, value):
        self.value_ = value

    def __str__(self):
        return self.value_


class CompileInfo(object):
    def __init__(self, patches: list, flags: list):
        self.patches_ = patches
        self.flags_ = flags

    def patches(self):
        return self.patches_

    def flags(self) -> list:
        return self.flags_

    def extend_flags(self, other_args):
        self.flags_.extend(other_args)


def build_command_cmake(source_dir_path: str, prefix_path: str, cmake_flags: list,
                        build_system=get_supported_build_system_by_name('ninja')):
    current_dir = os.getcwd()
    cmake_project_root_abs_path = '..'
    if not os.path.exists(cmake_project_root_abs_path):
        raise BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

    cmake_line = ['cmake', cmake_project_root_abs_path, '-G', build_system.cmake_generator_arg(),
                  '-DCMAKE_BUILD_TYPE=RELEASE']
    cmake_line.extend(cmake_flags)
    cmake_line.extend(['-DCMAKE_INSTALL_PREFIX={0}'.format(prefix_path)])
    try:
        os.chdir(source_dir_path)
        os.mkdir('build_cmake_release')
        os.chdir('build_cmake_release')
        subprocess.call(cmake_line)
        make_line = build_system.cmd_line()
        make_line.append('install')
        subprocess.call(make_line)
        if hasattr(shutil, 'which') and shutil.which('ldconfig'):
            subprocess.call(['ldconfig'])
    except Exception as ex:
        ex_str = str(ex)
        raise BuildError(ex_str)
    finally:
        os.chdir(current_dir)


def build_command_configure(compiler_flags: CompileInfo, patch_dir_path, prefix_path, executable='./configure',
                            build_system=get_supported_build_system_by_name('make')):
    # +x for exec file
    st = os.stat(executable)
    os.chmod(executable, st.st_mode | stat.S_IEXEC)

    for file_names in compiler_flags.patches():
        scan_dir = os.path.join(patch_dir_path, file_names)
        if os.path.exists(scan_dir):
            for diff in os.listdir(scan_dir):
                if re.match(r'.+\.patch', diff):
                    patch_file = os.path.join(scan_dir, diff)
                    line = 'patch -p0 < {0}'.format(patch_file)
                    subprocess.call(['bash', '-c', line])

    compile_cmd = [executable, '--prefix={0}'.format(prefix_path)]
    compile_cmd.extend(compiler_flags.flags())
    subprocess.call(compile_cmd)
    make_line = build_system.cmd_line()
    make_line.append('install')
    subprocess.call(make_line)
    if hasattr(shutil, 'which') and shutil.which('ldconfig'):
        subprocess.call(['ldconfig'])


def generate_fastogt_git_path(repo_name) -> str:
    return 'git@github.com:fastogt/%s.git' % repo_name


class BuildRequest(object):
    OPENSSL_SRC_ROOT = "https://www.openssl.org/source/"
    ARCH_OPENSSL_COMP = "gz"
    ARCH_OPENSSL_EXT = "tar." + ARCH_OPENSSL_COMP

    def __init__(self, platform, arch_name, patch_path, dir_path, prefix_path):
        platform_or_none = system_info.get_supported_platform_by_name(platform)
        if not platform_or_none:
            raise BuildError('invalid platform')

        arch_or_none = platform_or_none.architecture_by_arch_name(arch_name)
        if not arch_or_none:
            raise BuildError('invalid arch')

        if not prefix_path:
            prefix_path = arch_or_none.default_install_prefix_path()

        packages_types = platform_or_none.package_types()
        build_platform = platform_or_none.make_platform_by_arch(arch_or_none, packages_types)

        self.platform_ = build_platform
        build_dir_path = os.path.abspath(dir_path)
        if os.path.exists(build_dir_path):
            shutil.rmtree(build_dir_path)

        os.mkdir(build_dir_path)
        os.chdir(build_dir_path)

        self.build_dir_path_ = build_dir_path
        self.prefix_path_ = prefix_path
        self.patch_path_ = patch_path
        print("Build request for platform: {0}({1}) created".format(build_platform.name(), arch_or_none.name()))

    def platform(self):
        return self.platform_

    def platform_name(self) -> str:
        return self.platform_.name()

    def build_dir_path(self):
        return self.build_dir_path_

    def prefix_path(self):
        return self.prefix_path_

    def build_snappy(self):
        cloned_dir = utils.git_clone(generate_fastogt_git_path('snappy'))
        self._build_via_cmake(cloned_dir, ['-DBUILD_SHARED_LIBS=OFF', '-DSNAPPY_BUILD_TESTS=OFF'])

    def build_jsonc(self):
        cloned_dir = utils.git_clone(generate_fastogt_git_path('json-c'))
        self._build_via_cmake(cloned_dir, ['-DBUILD_SHARED_LIBS=OFF'])

    def build_libev(self):
        libev_compiler_flags = CompileInfo([], ['--with-pic', '--disable-shared', '--enable-static'])

        pwd = os.getcwd()
        cloned_dir = utils.git_clone(generate_fastogt_git_path('libev'))
        os.chdir(cloned_dir)

        autogen_libev = ['sh', 'autogen.sh']
        subprocess.call(autogen_libev)

        self._build_via_configure(libev_compiler_flags)
        os.chdir(pwd)

    def build_cpuid(self):
        cpuid_compiler_flags = CompileInfo([], ['--disable-shared', '--enable-static'])

        pwd = os.getcwd()
        cloned_dir = utils.git_clone(generate_fastogt_git_path('libcpuid'))
        os.chdir(cloned_dir)

        platform_name = self.platform_name()
        if platform_name == 'macosx':
            libtoolize_cpuid = ['glibtoolize']
        else:
            libtoolize_cpuid = ['libtoolize']
        subprocess.call(libtoolize_cpuid)

        autoreconf_cpuid = ['autoreconf', '--install']
        subprocess.call(autoreconf_cpuid)

        self._build_via_configure(cpuid_compiler_flags)

        os.chdir(pwd)

    def build_common(self, with_qt=False):
        cloned_dir = utils.git_clone(generate_fastogt_git_path('common'))
        cmake_flags = []
        if with_qt:
            cmake_flags.append('-DQT_ENABLED=ON')

        self._build_via_cmake(cloned_dir, cmake_flags)

    def build_openssl(self, version):
        compiler_flags = CompileInfo([], ['no-shared', 'no-unit-test'])
        url = '{0}openssl-{1}.{2}'.format(self.OPENSSL_SRC_ROOT, version, self.ARCH_OPENSSL_EXT)
        self._download_and_build_via_configure(url, compiler_flags, './config')

    def _clone_and_build_via_cmake(self, url, branch=None, remove_dot_git=True, cmake_flags=[]):
        cloned_dir = utils.git_clone(url, branch, remove_dot_git)
        self._build_via_cmake(cloned_dir, cmake_flags)

    def _build_via_cmake(self, directory, cmake_flags: list):
        build_command_cmake(directory, self.prefix_path_, cmake_flags)

    def _download_and_build_via_configure(self, url, compiler_flags: CompileInfo, executable='./configure'):
        pwd = os.getcwd()
        file_path = utils.download_file(url)
        extracted_folder = utils.extract_file(file_path)
        os.chdir(extracted_folder)
        build_command_configure(compiler_flags, self.patch_path_, self.prefix_path_, executable)
        os.chdir(pwd)

    def _build_via_configure(self, compiler_flags: CompileInfo, executable='./configure'):
        build_command_configure(compiler_flags, self.patch_path_, self.prefix_path_, executable)
