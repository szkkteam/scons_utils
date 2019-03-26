##
# This script includes generic build options:
#    release/debug, target os, target arch, cross toolchain, build environment etc
##
import os
import sys
import platform
import re
from   SCons.Script import *


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

######################################################################
# Platform (build target) specific options: SDK/NDK & toolchain
######################################################################
targets_support_cc = ['linux', 'windows']

def GetHost():
    # Fetch host from Python platform information and smash case
    host = platform.system().lower()

    if host not in host_target_map:
        msg = "\nError: building on host os '%s' is not currently supported.\n" % host
        Exit(msg)
    return host

def GetDefaultArch(target_os):
    # work out a reasonable default for target_arch if not specified by user
    default_arch = platform.machine()
    if target_os == 'windows':
        default_arch = default_arch.lower()
    if target_os == 'linux' and default_arch in os_arch_map[target_os]:
        default_arch = default_arch.lower()

    return default_arch

######################################################################
# this is where the setup of the construction envionment begins
######################################################################
def GetDefaultEnvironment(help_vars,target_os, target_arch):
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
    if not env.get('VERBOSE'):
        env['CCCOMSTR'] = "Compiling $TARGET"
        env['SHCCCOMSTR'] = "Compiling $TARGET"
        env['CXXCOMSTR'] = "Compiling $TARGET"
        env['SHCXXCOMSTR'] = "Compiling $TARGET"
        env['LINKCOMSTR'] = "Linking $TARGET"
        env['SHLINKCOMSTR'] = "Linking shared object $TARGET"
        env['ARCOMSTR'] = "Archiving $TARGET"
        env['RANLIBCOMSTR'] = "Indexing Archive $TARGET"

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

    return env