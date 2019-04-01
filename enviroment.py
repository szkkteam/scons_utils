##
# This script includes generic build options:
#    release/debug, target os, target arch, cross toolchain, build environment etc
##
import os
import sys
import platform
import re
from   SCons.Script import *
from utils import AppendEnviroment

project_version = '0.1.0'

# Map of build host to possible target os
host_target_map = {
    'linux': ['linux'],
    'windows': ['windows']
    #TODO: support more pre-build target.
}

# Map of target os to possible target architecture
os_arch_map = {
    'linux': [
        'x86', 'x86_64', 'arm', 'armv7l', 'arm-v7a', 'armeabi-v7a', 'arm64', 'mips',
        'mipsel', 'mips64', 'mips64el', 'i386', 'powerpc', 'sparc', 'aarch64',
        'armv6l', 'armv7l'
    ],
    'windows': ['x86', 'amd64', 'arm']
}


BASE_VARIANTS_ENV_EXTENSIONS = {
    'debug': dict(
        # Extra flags for debug builds
    ),
    'release': dict(
        # Extra flags for release builds
    ),
}

def listify(args):
    """Return args as a list.
    If already a list - returned as is.
    If a single instance of something that isn't a list, return it in a list.
    If "empty" (None or whatever), return a zero-length list ([]).
    """
    if args:
        if isinstance(args, list):
            return args
        return [args]
    return []

def remove_redundant(args):
    args = listify(args)
    if len(args) != len(set(args)):
        # error_inconsistent_module_list
        args = list(set(args))  # silently remove redundant items
    return args

def intersection(*args):
    """Return the intersection of all iterables passed."""
    args = list(args)
    result = set(listify(args.pop(0)))
    while args and result:
        # Finish the loop either when args is consumed, or result is empty
        result.intersection_update(listify(args.pop(0)))
    return result

"""
def _targets(target_list):
    if target_list:
        target_lists = set(BASE_TARGET_ENV_EXTENSIONS.keys() + target_list.keys())
    else:
        target_lists = set(BASE_TARGET_ENV_EXTENSIONS.keys())
    for target in target_lists:
        # Skip "hidden" records
        yield target
"""
def _variants(variant_list):
    variant_list = variant_list.keys()
    for variant in variant_list:
        # Skip "hidden" records
        yield variant

######################################################################
# Platform (build target) specific options: SDK/NDK & toolchain
######################################################################
targets_support_cc = ['linux', 'windows']


class QEnvironment(object):
    def __init__(self, env=None, variant_list=None):
        # Load an already created environment or create a default
        if env:
            self._env = env
        else:
            self._env = QEnvironment.GetDefaultEnvironment(self.InitializeCommandLineOptions())

        variants_list = BASE_VARIANTS_ENV_EXTENSIONS
        if variant_list:
            variants_list.update(variant_list)
            # Load the targets in to the environment
        self._getCommandLineVariants(variants_list)

        self._variants_list = variants_list

        # Load the os specific config
        self.GetPlatformConfig()


    def _getCommandLineVariants(self, variant_list):
        # If a target is activated in the external environment - use it
        if 'BUILD_TARGET' in os.environ:
            active_variant = os.environ['BUILD_TARGET']
            if not active_variant in _variants(variant_list):
                msg = "\nError: %s (from env) is not a known target." % (active_variant)
                Exit(msg)
            print('scons: Using active target "%s" from your environment' % (active_variant))
            self._active_variants = [active_variant]
        else:
            # If specific variant target specified, skip processing other variants
            # Otherwise, include all known variants
            self._active_variants = (
            set(_variants(variant_list)).intersection(COMMAND_LINE_TARGETS)  # pylint: disable=undefined-variable
            or list(_variants(variant_list)))

            # Remove the defined variant targets if other target is specified.
            # Otherwise use the defined variant as target.
            intersect_targets = set(self._active_variants).intersection(BUILD_TARGETS)
            if len(intersect_targets) > 0 and (len(BUILD_TARGETS) > len(intersect_targets)):
                [BUILD_TARGETS.remove(target) for target in intersect_targets]

    @property
    def targets(self):
        return self._active_variants

    @property
    def env(self):
        return self._env

    @staticmethod
    def GetHost():
        # Fetch host from Python platform information and smash case
        host = platform.system().lower()

        if host not in host_target_map:
            msg = "\nError: building on host os '%s' is not currently supported.\n" % host
            Exit(msg)
        return host

    @staticmethod
    def GetDefaultArch(target_os):
        # work out a reasonable default for target_arch if not specified by user
        default_arch = platform.machine()
        if target_os == 'windows':
            default_arch = default_arch.lower()
        if target_os == 'linux' and default_arch in os_arch_map[target_os]:
            default_arch = default_arch.lower()

        return default_arch

    @staticmethod
    def GetTargetOs():
        host = QEnvironment.GetHost()
        target_os = ARGUMENTS.get('TARGET_OS', host).lower()

        if target_os not in host_target_map[host]:
            msg = "\nError: host '%s' cannot currently build target '%s'" % (host, target_os)
            msg += "\n\tchoices: %s\n" % host_target_map[host]
            Exit(msg)

        return target_os

    @staticmethod
    def GetTargetArch(target_os):
        target_arch = ARGUMENTS.get('TARGET_ARCH', QEnvironment.GetDefaultArch(target_os))  # target arch
        if target_arch not in os_arch_map[target_os]:
            msg = "\nError: target os '%s' cannot currently build target '%s'" % (target_os, target_arch)
            msg += "\n\tchoices: %s\n" % os_arch_map[target_os]
            Exit(msg)

        return target_arch

    def Clone(self):
        return QEnvironment(self.env.Clone(), self._variants_list)

    def ApplyVariant(self, variant):
        # TODO: Seperate override and extensions
        if variant in self._active_variants:
            # Store the selected variant in the environment
            self.env['VARIANT'] = variant
            self.env.Append(**self._variants_list[variant])

            # Setup the build directory
            self.env.SetDir(self.env.GetLaunchDir())

            # If the variant target is still present in the build targets, add as an alias
            if variant in BUILD_TARGETS:
                # Create an alias for the target
                # TODO: This shall be placed to builder.py where the prog is built.
                self.env.Alias(variant, self.env['BUILD_DIR'])

        else:
            msg = "\nError: variant '%s' not specified." % (variant)
            msg += "\n\tchoices: %s\n" % self._active_variants
            Exit(msg)


    ######################################################################
    # Common build options
    ######################################################################
    def InitializeCommandLineOptions(self):

        host = QEnvironment.GetHost()

        target_os = QEnvironment.GetTargetOs()

        # generate a list of unique targets: convert to set() for uniqueness,
        # then convert back to a list
        targetlist = list(set(x for l in list(host_target_map.values()) for x in l))

        default_arch = QEnvironment.GetDefaultArch(target_os)

        if ARGUMENTS.get('RUN_TEST') == 'ON':
            logging_default = False
        else:
            release_mode = False
            if ARGUMENTS.get('RELEASE', True) in [
                'y', 'yes', 'true', 't', '1', 'on', 'all', True
            ]:
                release_mode = True
            logging_default = (release_mode is False)

        help_vars = Variables()
        help_vars.AddVariables(
                        ('PROJECT_VERSION',
                         'The version of Scons Utils',
                         project_version),
            EnumVariable('VERBOSE',
                         'Show compilation. Format: 0=minimal, 1=full, 2=debug',
                         default='ON',
                         allowed_values=('OFF', 'ON', 'DEBUG')),
            BoolVariable('RELEASE',
                         'Build for release?',
                         default=True),
            EnumVariable('TARGET_OS',
                         'Target platform',
                         default=host,
                         allowed_values=targetlist),
            EnumVariable('BUILD_TESTS',
                         'Build unit tests',
                         default='ON',
                         allowed_values=('ON', 'OFF')),
            EnumVariable('TARGET_ARCH',
                         'Target architecture',
                         default=default_arch,
                         allowed_values=os_arch_map[target_os]),
            EnumVariable('RUN_TEST',
                         'Run unit tests',
                         default='ON',
                         allowed_values=('ON', 'OFF')),
            BoolVariable('LOGGING',
                         'Enable stack logging',
                         default=logging_default),
            EnumVariable('LOG_LEVEL',
                         'Enable stack logging level',
                         default='DEBUG',
                         allowed_values=('DEBUG', 'INFO', 'ERROR', 'WARNING', 'FATAL')),
            EnumVariable('BUILD_SAMPLE',
                         'Build with sample',
                         default='ON',
                         allowed_values=('ON', 'OFF')),
            BoolVariable('WITH_ENV',
                         'Use compiler options from environment',
                         default=False),

        )

        ######################################################################
        # Platform (build target) specific options
        ######################################################################
        if target_os in ['linux']:
            # Build option to enable failing build if warnings encountered.
            # May need to be off for developing with newer compilers which
            # are stricter about emitting warnings. Defaults to true so
            # developer builds and gerrit builds have all warnings examined.
            help_vars.Add(
                BoolVariable('ERROR_ON_WARN',
                             'Make all compiler warnings into errors.',
                             default=False))

        if target_os == 'windows':
            # Builds differ based on Visual Studio version
            #   For VS2013, MSVC_VERSION is '12.0'.
            #   For VS2015, MSVC_VERSION is '14.0'.
            #   For VS2017, MSVC_VERSION is '14.1'.
            # Default value is None, which means SCons will pick
            help_vars.Add(
                EnumVariable('MSVC_VERSION',
                             'MSVC compiler version - Windows',
                             default=None,
                             allowed_values=('12.0', '14.0', '14.1')))

        ######################################################################
        # Platform (build target) specific options: SDK/NDK & toolchain
        ######################################################################
        if target_os in targets_support_cc:
            # Set cross compile toolchain
            help_vars.Add('TC_PREFIX',
                          "Toolchain prefix (Generally only required for cross-compiling)",
                          default=None)
            help_vars.Add(
                PathVariable('TC_PATH',
                             'Toolchain path (Generally only required for cross-compiling)',
                             default=None,
                             validator=PathVariable.PathAccept))

        return help_vars

######################################################################
# this is where the setup of the construction envionment begins
######################################################################
    @staticmethod
    def GetDefaultEnvironment(help_vars):
        target_os = QEnvironment.GetTargetOs()
        target_arch = QEnvironment.GetTargetArch(target_os)
        env = Environment(
            variables=help_vars,
            tools=['default', 'textfile'],
            TARGET_ARCH=target_arch,
            TARGET_OS=target_os,
            #PREFIX=GetOption('prefix'),
            LIB_INSTALL_DIR=ARGUMENTS.get('LIB_INSTALL_DIR')  #for 64bit build
        )

        if env.get('WITH_ENV'):
            env['ENV'] = os.environ
            if 'CC' in os.environ:
                env['CC'] = Split(os.environ['CC'])
                print("using CC from environment: %s" % env['CC'])
            if 'CXX' in os.environ:
                env['CXX'] = Split(os.environ['CXX'])
                print("using CXX from environment: %s" % env['CXX'])
            if 'CFLAGS' in os.environ:
                env['CFLAGS'] = Split(os.environ['CFLAGS'])
                print("using CFLAGS from environment: %s" % env['CFLAGS'])
            if 'CXXFLAGS' in os.environ:
                env['CXXFLAGS'] = Split(os.environ['CXXFLAGS'])
                print("using CXXFLAGS from environment: %s" % env['CXXFLAGS'])
            if 'CCFLAGS' in os.environ:
                env['CCFLAGS'] = Split(os.environ['CCFLAGS'])
                print("using CCFLAGS from environment: %s" % env['CCFLAGS'])
            if 'CPPFLAGS' in os.environ:
                env['CPPFLAGS'] = Split(os.environ['CPPFLAGS'])
                print("using CPPFLAGS from environment: %s" % env['CPPFLAGS'])
            if 'LDFLAGS' in os.environ:
                env['LINKFLAGS'] = Split(os.environ['LDFLAGS'])
                print("using LDFLAGS/LINKFLAGS from environment: %s" % env['LINKFLAGS'])

        # set quieter build messages unless verbose mode was requested
        if env.get('VERBOSE') == 'ON':
            env['CCCOMSTR'] = "Compiling: $TARGET"
            env['SHCCCOMSTR'] = "Compiling: $TARGET"
            env['CXXCOMSTR'] = "Compiling: $TARGET"
            env['SHCXXCOMSTR'] = "Compiling: $TARGET"
            env['LINKCOMSTR'] = "Linking: $TARGET"
            env['SHLINKCOMSTR'] = "Linking shared object: $TARGET"
            env['ARCOMSTR'] = "Archiving: $TARGET"
            env['RANLIBCOMSTR'] = "Indexing Archive: $TARGET"
        elif env.get('VERBOSE') == 'DEBUG':
            debugCCCOMSTR = '--------Compiling "$TARGET":--------\n'
            for index, item in enumerate(env['CCCOM'].split()):
                debugCCCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['CCCOMSTR'] = debugCCCOMSTR

            debugSHCCCOMSTR = '--------Compiling "$SOURCES":--------\n'
            for index, item in enumerate(env['SHCCCOM'].split()):
                debugSHCCCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['SHCCCOMSTR'] = debugSHCCCOMSTR

            debugCXXCOMSTR = '--------Compiling "$SOURCES":--------\n'
            for index, item in enumerate(env['CXXCOM'].split()):
                debugCXXCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['CXXCOMSTR'] = debugCXXCOMSTR

            debugSHCXXCOMSTR = '--------Compiling "$SOURCES":--------\n'
            for index, item in enumerate(env['SHCXXCOM'].split()):
                debugSHCXXCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['SHCXXCOMSTR'] = debugSHCXXCOMSTR

            debugLINKCOMSTR = '--------Linking "$TARGET":--------\n'
            for index, item in enumerate(env['LINKCOM'].split()):
                debugLINKCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['LINKCOMSTR'] = debugLINKCOMSTR

            #TODO: This generate an error
            #debugSHLINKCOMSTR = '--------Linking "$TARGET":--------\n'
            #for index, item in enumerate(env['SHLINKCOM'].split()):
            #    debugSHLINKCOMSTR += "%2d: %s\n" % (index + 1, item)
            #env['SHLINKCOMSTR'] = debugSHLINKCOMSTR

            debugARCOMSTR       = '--------Archiving to "$TARGET":--------\n'
            for index, item in enumerate(env['ARCOM'].split()):
                debugARCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['ARCOMSTR']     = debugARCOMSTR

            debugRANLIBCOMSTR       = '--------Indexing Archive "$TARGET":--------\n'
            for index, item in enumerate(env['RANLIBCOM'].split()):
                debugRANLIBCOMSTR += "%2d: %s\n" % (index + 1, item)
            env['RANLIBCOMSTR']     = debugRANLIBCOMSTR

        tc_set_msg = '''
    ************************************ Warning **********************************
    * Warning: TC_PREFIX and/or TC_PATH is set in the environment.
    * This means a non-default compilation toolchain will be used.
    * If this is not what you expected you should unset, or it
    * may lead to unexpected results.
    *******************************************************************************
        '''
        if target_os in targets_support_cc:
            prefix = env.get('TC_PREFIX')
            tc_path = env.get('TC_PATH')
            if prefix:
                env.Replace(CC=prefix + env.get('CC', 'gcc'))
                env.Replace(CXX=prefix + env.get('CXX', 'g++'))
                env.Replace(AR=prefix + env.get('AR', 'ar'))
                env.Replace(AS=prefix + env.get('AS', 'as'))
                env.Replace(RANLIB=prefix + env.get('RANLIB', 'ranlib'))

            if tc_path:
                env.PrependENVPath('PATH', tc_path)
                sys_root = os.path.abspath(tc_path + '/../')
                env.AppendUnique(CCFLAGS=['--sysroot=' + sys_root])
                env.AppendUnique(LINKFLAGS=['--sysroot=' + sys_root])

            if prefix or tc_path:
                print(tc_set_msg)

        # Ensure scons is able to change its working directory
        env.SConscriptChdir(1)

        AppendEnviroment(env)

        #print (env.Dump())
        env['ROOT_DIR'] = env.GetLaunchDir() + '/..'

    ######################################################################
    # Setting global compiler flags
    ######################################################################
        # TODO: Are they really needed?
        #env.AppendUnique(LIBPATH = [env.get('BUILD_DIR')])
        #if not env.get('PREFIX') and not env.get('LIB_INSTALL_DIR'):
           #env.AppendUnique(LIBPATH = [env.get('BUILD_DIR') + '/deploy'])
        #if (target_os not in ['windows']):
            #env.AppendUnique(CPPDEFINES=['WITH_POSIX'])

        # Load config of target os
        #env.SConscript(GetOption('site_dir') + '/platforms/' + target_os + '/SConscript', must_exist=1, exports = ['env'] )

        # TODO: search for RPATH and ORIGIN, this is probably needed, but not here.
        #if env.get('CROSS_COMPILE'):
            #env.Append(RPATH=env.Literal('\\$$ORIGIN'))
        #else:
            #env.Append(RPATH=env.get('BUILD_DIR'))

        # Delete the temp files of configuration
        if env.GetOption('clean'):
            dir = env.get('SRC_DIR')

            if os.path.exists(dir + '/config.log'):
                Execute(Delete(dir + '/config.log'))
            if os.path.exists(dir + '/.sconsign.dblite'):
                Execute(Delete(dir + '/.sconsign.dblite'))
            if os.path.exists(dir + '/.sconf_temp'):
                Execute(Delete(dir + '/.sconf_temp'))

        return env

    def GetPlatformConfig(self, path_to_config = ""):
        # Load config of target os
        env = self.env
        if path_to_config:
            self.env.SConscript(path_to_config, must_exist=1, exports=['env'])
        else:
            self.env.SConscript(GetOption('site_dir') + '/platforms/' + QEnvironment.GetTargetOs() + '/SConscript', must_exist=1, exports=['env'])
