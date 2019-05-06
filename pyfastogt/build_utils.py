import os
import stat
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
                           BuildSystem('make', ['make', '-j2'], 'Unix Makefiles'),
                           BuildSystem('gmake', ['gmake', '-j2'], 'Unix Makefiles')]


def get_supported_build_system_by_name(name) -> BuildSystem:
    return next((x for x in SUPPORTED_BUILD_SYSTEMS if x.name() == name), None)


class BuildError(Exception):
    def __init__(self, value):
        self.value_ = value

    def __str__(self):
        return self.value_


# must be in cmake folder
def build_command_cmake(prefix_path: str, cmake_flags: list, build_type='RELEASE',
                        build_system=get_supported_build_system_by_name('ninja')):
    cmake_project_root_abs_path = '..'
    if not os.path.exists(cmake_project_root_abs_path):
        raise BuildError('invalid cmake_project_root_path: %s' % cmake_project_root_abs_path)

    abs_prefix_path = os.path.expanduser(prefix_path)
    cmake_line = ['cmake', cmake_project_root_abs_path, '-G', build_system.cmake_generator_arg(),
                  '-DCMAKE_BUILD_TYPE=%s' % build_type]
    cmake_line.extend(cmake_flags)
    cmake_line.extend(['-DCMAKE_INSTALL_PREFIX=%s' % abs_prefix_path])
    try:
        build_dir_name = 'build_cmake_%s' % build_type.lower()
        if os.path.exists(build_dir_name):
            shutil.rmtree(build_dir_name)

        os.mkdir(build_dir_name)
        os.chdir(build_dir_name)
        subprocess.call(cmake_line)
        make_line = build_system.cmd_line()
        subprocess.call(make_line)
        make_line.append('install')
        subprocess.call(make_line)
        if hasattr(shutil, 'which') and shutil.which('ldconfig'):
            subprocess.call(['ldconfig'])
    except Exception as ex:
        ex_str = str(ex)
        raise BuildError(ex_str)


# must be in configure folder
def build_command_configure(compiler_flags: list, prefix_path, executable='./configure',
                            build_system=get_supported_build_system_by_name('make')):
    # +x for exec file
    st = os.stat(executable)
    os.chmod(executable, st.st_mode | stat.S_IEXEC)

    abs_prefix_path = os.path.expanduser(prefix_path)
    compile_cmd = [executable, '--prefix={0}'.format(abs_prefix_path)]
    compile_cmd.extend(compiler_flags)
    subprocess.call(compile_cmd)
    make_line = build_system.cmd_line()
    subprocess.call(make_line)
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

    def __init__(self, platform: str, arch_name: str, dir_path: str, prefix_path: str):
        platform_or_none = system_info.get_supported_platform_by_name(platform)
        if not platform_or_none:
            raise BuildError('invalid platform')

        arch_or_none = platform_or_none.get_architecture_by_arch_name(arch_name)
        if not arch_or_none:
            raise BuildError('invalid arch')

        if not prefix_path:
            prefix_path = arch_or_none.default_install_prefix_path()
        abs_prefix_path = os.path.expanduser(prefix_path)

        packages_types = platform_or_none.package_types()
        build_platform = platform_or_none.make_platform_by_arch(arch_or_none, packages_types)

        os.environ['PKG_CONFIG_PATH'] = '$PKG_CONFIG_PATH:%s/lib/pkgconfig/' % abs_prefix_path
        env = build_platform.env_variables()
        for key, value in env.items():
            os.environ[key] = value

        self.platform_ = build_platform
        build_dir_path = os.path.abspath(dir_path)
        if os.path.exists(build_dir_path):
            shutil.rmtree(build_dir_path)

        os.mkdir(build_dir_path)
        os.chdir(build_dir_path)

        self.build_dir_path_ = build_dir_path
        self.prefix_path_ = abs_prefix_path
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
        self._clone_and_build_via_cmake(generate_fastogt_git_path('snappy'),
                                        ['-DBUILD_SHARED_LIBS=OFF', '-DSNAPPY_BUILD_TESTS=OFF'])

    def build_jsonc(self):
        self._clone_and_build_via_cmake(generate_fastogt_git_path('json-c'), ['-DBUILD_SHARED_LIBS=OFF'])

    def build_libev(self):
        libev_compiler_flags = ['--with-pic', '--disable-shared', '--enable-static']
        self._clone_and_build_via_autogen(generate_fastogt_git_path('libev'), libev_compiler_flags)

    def build_cpuid(self):
        cpuid_compiler_flags = ['--disable-shared', '--enable-static']

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
        cmake_flags = []
        if with_qt:
            cmake_flags.append('-DQT_ENABLED=ON')

        self._clone_and_build_via_cmake(generate_fastogt_git_path('common'), cmake_flags)

    def build_openssl(self, version):
        compiler_flags = ['no-shared', 'no-unit-test']
        if self.platform_name() == 'android':
            compiler_flags.extend(['no-asm'])
        url = '{0}openssl-{1}.{2}'.format(self.OPENSSL_SRC_ROOT, version, self.ARCH_OPENSSL_EXT)
        self._download_and_build_via_configure(url, compiler_flags, './config', False)

    # install packages
    def _install_package(self, name: str):
        self.platform_.install_package(name)

    # clone
    def _clone_and_build_via_cmake(self, url: str, cmake_flags: list, branch=None, remove_dot_git=True):
        pwd = os.getcwd()
        cloned_dir = utils.git_clone(url, branch, remove_dot_git)
        os.chdir(cloned_dir)
        self._build_via_cmake(cmake_flags)
        os.chdir(pwd)

    def _clone_and_build_via_configure(self, url: str, compiler_flags: list, executable='./configure',
                                       use_platform_flags=True, branch=None, remove_dot_git=True):
        pwd = os.getcwd()
        cloned_dir = utils.git_clone(url, branch, remove_dot_git)
        os.chdir(cloned_dir)
        self._build_via_configure(compiler_flags, executable, use_platform_flags)
        os.chdir(pwd)

    def _clone_and_build_via_autogen(self, url: str, compiler_flags: list, executable='./configure',
                                     use_platform_flags=True, branch=None,
                                     remove_dot_git=True):
        pwd = os.getcwd()
        cloned_dir = utils.git_clone(url, branch, remove_dot_git)
        os.chdir(cloned_dir)
        self._build_via_autogen(compiler_flags, executable, use_platform_flags)
        os.chdir(pwd)

    # download
    def _download_and_build_via_cmake(self, url: str, cmake_flags: list):
        pwd = os.getcwd()
        file_path = utils.download_file(url)
        extracted_folder = utils.extract_file(file_path)
        os.chdir(extracted_folder)
        self._build_via_cmake(cmake_flags)
        os.chdir(pwd)

    def _download_and_build_via_autogen(self, url: str, compiler_flags: list, executable='./configure',
                                        use_platform_flags=True):
        pwd = os.getcwd()
        file_path = utils.download_file(url)
        extracted_folder = utils.extract_file(file_path)
        os.chdir(extracted_folder)
        self._build_via_autogen(compiler_flags, executable, use_platform_flags)
        os.chdir(pwd)

    def _download_and_build_via_configure(self, url: str, compiler_flags: list, executable='./configure',
                                          use_platform_flags=True):
        pwd = os.getcwd()
        file_path = utils.download_file(url)
        extracted_folder = utils.extract_file(file_path)
        os.chdir(extracted_folder)
        self._build_via_configure(compiler_flags, executable, use_platform_flags)
        os.chdir(pwd)

    # build
    def _build_via_autogen(self, compiler_flags: list, executable='./configure', use_platform_flags=True):
        autogen_line = ['sh', 'autogen.sh']
        subprocess.call(autogen_line)
        self._build_via_configure(compiler_flags, executable, use_platform_flags)

    # raw build
    def _build_via_cmake(self, cmake_flags: list, use_platform_flags=True):
        cmake_flags_extended = cmake_flags
        if use_platform_flags:
            cmake_flags_extended.extend(self.platform_.cmake_specific_flags())
        build_command_cmake(self.prefix_path_, cmake_flags)

    def _build_via_configure(self, compiler_flags: list, executable='./configure', use_platform_flags=True):
        compiler_flags_extended = compiler_flags
        if use_platform_flags:
            compiler_flags_extended.extend(self.platform_.configure_specific_flags())
        build_command_configure(compiler_flags_extended, self.prefix_path_, executable)
