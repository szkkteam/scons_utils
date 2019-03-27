##
# This script includes generic build options:
#    release/debug, target os, target arch, cross toolchain, build environment etc
##
import os
import sys
import platform
import re
#import SCons.Variables
from   SCons.Script import *
from enviroment import *

######################################################################
# Common build options
######################################################################

def GetTargetOs():
    host = GetHost()
    target_os = ARGUMENTS.get('TARGET_OS', host).lower()

    if target_os not in host_target_map[host]:
        msg = "\nError: host '%s' cannot currently build target '%s'" % (host, target_os)
        msg += "\n\tchoices: %s\n" % host_target_map[host]
        Exit(msg)

    return target_os

def GetTargetArch(target_os):
    target_arch = ARGUMENTS.get('TARGET_ARCH', GetDefaultArch(target_os))  # target arch
    if target_arch not in os_arch_map[target_os]:
        msg = "\nError: target os '%s' cannot currently build target '%s'" % (target_os, target_arch)
        msg += "\n\tchoices: %s\n" % os_arch_map[target_os]
        Exit(msg)

    return target_arch

def InitializeCommandLineOptions(project_version):

    host = GetHost()

    target_os = GetTargetOs()

    # generate a list of unique targets: convert to set() for uniqueness,
    # then convert back to a list
    targetlist = list(set(x for l in list(host_target_map.values()) for x in l))

    default_arch = GetDefaultArch(target_os)

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
