import platform
import subprocess
from abc import ABCMeta, abstractmethod


class Architecture(object):
    def __init__(self, arch_str, bit, default_install_prefix_path):
        self.name_ = arch_str
        self.bit_ = bit
        self.default_install_prefix_path_ = default_install_prefix_path

    def name(self):
        return self.name_

    def bit(self):
        return self.bit_

    def default_install_prefix_path(self):
        return self.default_install_prefix_path_


class Platform(metaclass=ABCMeta):
    def __init__(self, name: str, arch: Architecture, package_types: list):
        self.name_ = name
        self.arch_ = arch
        self.package_types_ = package_types

    def name(self) -> str:
        return self.name_

    def arch(self) -> Architecture:
        return self.arch_

    def package_types(self) -> list:
        return self.package_types_

    @abstractmethod
    def install_package(self, name):
        pass


class SupportedPlatforms(metaclass=ABCMeta):
    def __init__(self, name: str, archs: list, package_types: list):
        self.name_ = name
        self.archs_ = archs
        self.package_types_ = package_types

    def name(self) -> str:
        return self.name_

    def archs(self) -> list:
        return self.archs_

    def package_types(self) -> list:
        return self.package_types_

    def architecture_by_arch_name(self, arch_name):
        for curr_arch in self.archs_:
            if curr_arch.name() == arch_name:
                return curr_arch

        return None

    @abstractmethod
    def make_platform_by_arch(self, arch, package_types) -> Platform:  # factory method
        pass


def linux_get_dist():
    """
    Return the running distribution group
    RHEL: RHEL, CENTOS, FEDORA
    DEBIAN: UBUNTU, DEBIAN, LINUXMINT
    """
    linux_tuple = platform.linux_distribution()
    dist_name = linux_tuple[0]
    dist_name_upper = dist_name.upper()

    if dist_name_upper in ["RHEL", "CENTOS LINUX", "FEDORA"]:
        return "RHEL"
    elif dist_name_upper in ["DEBIAN", "UBUNTU", "LINUXMINT"]:
        return "DEBIAN"
    elif dist_name_upper in ["ARCH"]:
        return "ARCH"
    raise NotImplemented("Unknown platform '%s'" % dist_name)


# Linux platforms

class DebianPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'linux', arch, package_types)

    def install_package(self, name):
        subprocess.call(['apt-get', '-y', '--no-install-recommends', 'install', name])


class RedHatPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'linux', arch, package_types)

    def install_package(self, name):
        subprocess.call(['yum', '-y', 'install', name])


class ArchPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'linux', arch, package_types)

    def install_package(self, name):
        subprocess.call(['pacman', '-S', '--noconfirm', name])


class LinuxPlatforms(SupportedPlatforms):
    def __init__(self):
        SupportedPlatforms.__init__(self, 'linux', [Architecture('x86_64', 64, '/usr/local'),
                                                    Architecture('i386', 32, '/usr/local'),
                                                    Architecture('i686', 32, '/usr/local'),
                                                    Architecture('aarch64', 64, '/usr/local'),
                                                    Architecture('armv7l', 32, '/usr/local'),
                                                    Architecture('armv6l', 32, '/usr/local')],
                                    ['DEB', 'RPM', 'TGZ'])

    def make_platform_by_arch(self, arch, package_types) -> Platform:
        distr = linux_get_dist()
        if distr == 'DEBIAN':
            return DebianPlatform(arch, package_types)
        elif distr == 'RHEL':
            return RedHatPlatform(arch, package_types)
        elif distr == 'ARCH':
            return ArchPlatform(arch, package_types)
        raise NotImplemented("Unknown distribution '%s'" % distr)


# Windows platforms
class WindowsMingwPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'windows', arch, package_types)

    def install_package(self, name):
        subprocess.call(['pacman', '-S', '--noconfirm', name])


class WindowsPlatforms(SupportedPlatforms):
    def __init__(self):
        SupportedPlatforms.__init__(self, 'windows',
                                    [Architecture('x86_64', 64, '/mingw64'),
                                     Architecture('AMD64', 64, '/mingw64'),
                                     Architecture('i386', 32, '/mingw32'),
                                     Architecture('i686', 32, '/mingw32')],
                                    ['NSIS', 'ZIP'])

    def make_platform_by_arch(self, arch, package_types) -> Platform:
        return WindowsMingwPlatform(arch, package_types)


# MacOSX platforms
class MacOSXCommonPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'macosx', arch, package_types)

    def install_package(self, name):
        subprocess.call(['port', 'install', name])


class MacOSXPlatforms(SupportedPlatforms):
    def __init__(self):
        SupportedPlatforms.__init__(self, 'macosx', [Architecture('x86_64', 64, '/usr/local')], ['DragNDrop', 'ZIP'])

    def make_platform_by_arch(self, arch, package_types) -> Platform:
        return MacOSXCommonPlatform(arch, package_types)


# FreeBSD platforms
class FreeBSDCommonPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'freebsd', arch, package_types)

    def install_package(self, name):
        raise NotImplementedError('You need to define a install_package method!')


class FreeBSDPlatforms(SupportedPlatforms):
    def __init__(self):
        SupportedPlatforms.__init__(self, 'freebsd', [Architecture('x86_64', 64, '/usr/local'),
                                                      Architecture('amd64', 64, '/usr/local')], ['TGZ'])

    def make_platform_by_arch(self, arch, package_types) -> Platform:
        return FreeBSDCommonPlatform(arch, package_types)


# Android platforms
class AndroidCommonPlatform(Platform):
    def __init__(self, arch, package_types):
        Platform.__init__(self, 'android', arch, package_types)

    def install_package(self, name):
        raise NotImplementedError('You need to define a install_package method!')


class AndroidPlatforms(SupportedPlatforms):
    PLATFORM = 'android-16'

    def __init__(self):
        SupportedPlatforms.__init__(self, 'android',
                                    [Architecture('arm', 32,
                                                  '/opt/android-ndk/platforms/' + self.PLATFORM + '/arch-arm/usr/'),
                                     Architecture('i386', 32,
                                                  '/opt/android-ndk/platforms/' + self.PLATFORM + '/arch-x86/usr/')],
                                    ['APK'])

    def make_platform_by_arch(self, arch, package_types) -> Platform:
        return AndroidCommonPlatform(arch, package_types)


SUPPORTED_PLATFORMS = [LinuxPlatforms(), WindowsPlatforms(), MacOSXPlatforms(), FreeBSDPlatforms(), AndroidPlatforms()]


def get_extension_by_package(package_type) -> str:
    if package_type == 'DEB':
        return 'deb'
    elif package_type == 'RPM':
        return 'rpm'
    elif package_type == 'TGZ':
        return 'tar.gz'
    elif package_type == 'NSIS':
        return 'exe'
    elif package_type == 'ZIP':
        return 'zip'
    elif package_type == 'DragNDrop':
        return 'dmg'
    elif package_type == 'APK':
        return 'apk'
    else:
        return 'unknown'


def get_os() -> str:
    uname_str = platform.system()
    if 'MINGW' in uname_str:
        return 'windows'
    elif 'MSYS' in uname_str:
        return 'windows'
    elif uname_str == 'Windows':
        return 'windows'
    elif uname_str == 'Linux':
        return 'linux'
    elif uname_str == 'Darwin':
        return 'macosx'
    elif uname_str == 'FreeBSD':
        return 'freebsd'
    elif uname_str == 'Android':
        return 'android'
    else:
        return 'unknown'


def get_arch_name() -> str:
    return platform.machine()


def get_supported_platform_by_name(platform) -> SupportedPlatforms:
    return next((x for x in SUPPORTED_PLATFORMS if x.name() == platform), None)


class BuildSystem:
    def __init__(self, name, cmd_line, cmake_generator_arg):
        self.name_ = name
        self.cmd_line_ = cmd_line
        self.cmake_generator_arg_ = cmake_generator_arg

    def cmake_generator_arg(self):
        return self.cmake_generator_arg_

    def name(self):
        return self.name_

    def cmd_line(self):  # cmd + args
        return self.cmd_line_


SUPPORTED_BUILD_SYSTEMS = [BuildSystem('ninja', ['ninja'], '-GNinja'),
                           BuildSystem('make', ['make', '-jn'], '-GUnix Makefiles'),
                           BuildSystem('gmake', ['gmake', '-jn'], '-GUnix Makefiles')]


def get_supported_build_system_by_name(name) -> BuildSystem:
    return next((x for x in SUPPORTED_BUILD_SYSTEMS if x.name() == name), None)


def stable_path(path) -> str:
    if get_os() == 'windows':
        return path.replace("\\", "/")

    return path.replace("\\", "/")
