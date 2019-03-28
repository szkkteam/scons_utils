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

######################################################################
# this is where the setup of the construction envionment begins
######################################################################
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
    env.SetDir(env.GetLaunchDir())
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

def GetGetPlatformConfig(env):
    # Load config of target os
    env.SConscript(GetOption('site_dir') + '/platforms/' + target_os + '/SConscript', must_exist=1, exports=['env'])

def SetBuildDirectory(env, dir, target):
    env.SetDir(env.GetLaunchDir())
    env['ROOT_DIR'] = env.GetLaunchDir() + '/..'
