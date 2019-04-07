##
# This script includes generic build options:
#    release/debug, target os, target arch, cross toolchain, build environment etc
##
import os
import sys
import platform
import re
from   SCons.Script import *
from utils import AppendEnviroment, listify, intersection
from config import *
#import copy

project_version = '0.1.0'


def _variants(variant_list):
    for variant in variant_list:
        # Skip "hidden" records
        yield variant


def GetHost():
    # Fetch host from Python platform information and smash case
    return platform.system().lower()

def GetDefaultArch(target_os):
    # work out a reasonable default for target_arch if not specified by user
    return  platform.machine()

def GetTargetOs():
    host = GetHost()
    return ARGUMENTS.get('TARGET_OS', host).lower()

def GetTargetArch(target_os):
    return ARGUMENTS.get('TARGET_ARCH', GetDefaultArch(target_os))  # target arch

######################################################################
# Platform (build target) specific options: SDK/NDK & toolchain
######################################################################
targets_support_cc = ['linux', 'windows']

class QEnvironment(object):
    def __init__(self, config_file=None, env=None):
        # Load the configuration paramters.
        self._config_file = config_file
        self._config = BuildConfig(config_file)

        # Load an already created environment or create a default
        if env:
            self._env = env
        else:
            self._env = QEnvironment.GetDefaultEnvironment(self.InitializeCommandLineOptions())

        variants_list = self._config.GetVariantNames()
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

    def _getHost(self):
        # Fetch host from Python platform information and smash case
        host = GetHost()

        # Get all the hosts
        host_found = False
        for os in self._config.GetPlatforms():
            if host in self._config.GetHosts(os):
                host_found = True

        if not host_found:
            msg = "\nError: building on host os '%s' is not currently supported.\n" % host
            Exit(msg)
        return host

    def _getDefaultArch(self, target_os):
        # work out a reasonable default for target_arch if not specified by user
        default_arch = GetDefaultArch(target_os)
        if target_os == 'windows':
            default_arch = default_arch.lower()
        if target_os == 'linux' and default_arch in self._config.GetArchitectures(target_os):
            default_arch = default_arch.lower()

        return default_arch

    def _getTargetOs(self):
        host = self._getHost()
        target_os = GetTargetOs()
        host_target_map = self._config.GetHosts(target_os)

        if host not in host_target_map :
            msg = "\nError: host '%s' cannot currently build target '%s'" % (host, target_os)
            msg += "\n\tchoices: %s\n" % host_target_map
            Exit(msg)

        return target_os

    def _getTargetArch(self, target_os):
        target_arch = GetTargetArch(target_os)
        os_arch_map = self._config.GetArchitectures(target_os)

        if target_arch not in os_arch_map:
            msg = "\nError: target os '%s' cannot currently build target '%s'" % (target_os, target_arch)
            msg += "\n\tchoices: %s\n" % os_arch_map
            Exit(msg)

        return target_arch

    def Clone(self):
        # TODO: Perform a normal copy operation, not re-initialize the class. Or avoid the double initialization
        return QEnvironment(self._config_file, self.env.Clone())

    def ApplyVariant(self, variant):
        if variant in self._active_variants:
            # Store the selected variant in the environment
            self.env['VARIANT'] = variant

            self.env.Replace(**self._config.GetVariantOverride(variant))
            self.env.Append(**self._config.GetVariantExtension(variant))

            # Setup the build directory
            self.env.SetDir(self.env.GetLaunchDir())

        else:
            msg = "\nError: variant '%s' not specified." % (variant)
            msg += "\n\tchoices: %s\n" % self._active_variants
            Exit(msg)


    ######################################################################
    # Common build options
    ######################################################################
    def InitializeCommandLineOptions(self):

        host = self._getHost()

        target_os = self._getTargetOs()

        # generate a list of unique targets: convert to set() for uniqueness,
        # then convert back to a list
        targetlist = self._config.GetPlatforms()

        default_arch = self._getDefaultArch(target_os)

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
                         default='OFF',
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
                         allowed_values=self._config.GetArchitectures(target_os)),
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
        target_os = GetTargetOs()
        target_arch = GetTargetArch(target_os)
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
        if env.get('VERBOSE') == 'OFF':
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

    def GetPlatformConfig(self):
        search_dir = [self.env.GetLaunchDir(), GetOption('site_dir')]
        target_os = self._getTargetOs()
        config_file = self._config.GetPlatformConfig(target_os)

        for base_dir in search_dir:
            path = os.path.normpath(base_dir + config_file)
            #path = os.path.join(base_dir, config_file)
            if os.path.exists(path):
                # Load config of target os
                print ("Loading configuration file \'%s\'." % path)
                env = self.env
                self.env.SConscript(path, must_exist=1, exports=['env'])
                break

