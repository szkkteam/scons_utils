import os
import sys
import platform
import re
from   SCons.Script import *
#from enviroment import GetTargetOs, GetTargetArch

######################################################################
# Convenience functions to "extend" SCons
######################################################################

#def set_dir(target_os, target_arch, *args, **kwargs):
def __set_dir(env, dir):
    #
    # Set the source and build directories
    #   Source directory: 'dir'
    #   Build directory: 'dir'/out/<target_os>/<target_arch>/<release or debug>/
    #   On windows, the build directory will be:
    #     'dir'/out/windows/<win32 or uwp>/<target_arch>/<release or debug>/
    #
    # You can get the directory as following:
    #   env.get('SRC_DIR')
    #   env.get('BUILD_DIR')
    #
    if not os.path.exists(dir + '/SConstruct'):
        msg = '''
*************************************** Error *********************************
* The directory (%s) seems not to be a buildable directory,
* no SConstruct file found.
*******************************************************************************
''' % dir
        Exit(msg)

    target_os = env['TARGET_OS']
    target_arch = env['TARGET_ARCH']

    build_dir = dir + '/out/' + '/%s/' + target_os + '/' + target_arch

    if env.get('RELEASE'):
        build_dir = build_dir + '/release/'
    else:
        build_dir = build_dir + '/debug/'

    env.VariantDir((build_dir % 'bin'), dir, duplicate=0)

    env.Replace(BUILD_DIR=(build_dir % 'bin'))
    env.Replace(SRC_DIR=dir)
    env.Replace(INSTALL_DIR=(build_dir % 'install'))
    env.Replace(LIBPATH=(build_dir % 'install'))


def __src_to_obj(env, src, home=''):
    '''
    Make sure builds happen in BUILD_DIR (by default they
    would happen in the directory of the source file)
    Note this does not seem to be used, VariantDir is used instead
    '''
    obj = env.get('BUILD_DIR') + src.replace(home, '')
    if env.get('OBJSUFFIX'):
        obj += env.get('OBJSUFFIX')
    return env.Object(obj, src)


def __install(env, ienv, targets, name=''):
    '''
    Copy files to internal place (not for install to system)
    only use UserInstall() for copying files to system using "scons install"
    '''
    for filename in ienv.GetBuildPath(targets):
        basename = os.path.basename(filename)
        dst = env.get('BUILD_DIR') + basename
        i_n = Command(dst, filename, Copy("$TARGET", "$SOURCE"))
        if '' == name:
            name = basename
        ienv.Alias(name, i_n)
        env.AppendUnique(TS=[name])


def __chrpath(target, source, env):
    '''
    Remove RPATH (if installed elsewhere)
    '''
    target_os = env['TARGET_OS']
    if target_os in ['linux', 'tizen']:
        env.Command(None, target, 'chrpath -d $SOURCE')

def __installlib(env, ienv, targets):
    '''
    Install files to system, using "scons install" and remove rpath info if present
    If prefix or lib install dir is not specified, for developer convenience
    files are copied in relative "deploy" folder along executables (rpath is kept)
    to avoid overlap with "internal place" above
    '''
    user_prefix = env.get('PREFIX')
    if user_prefix:
        user_lib = env.get('LIB_INSTALL_DIR')
        if user_lib:
            dst_dir  = user_lib
        else:
            dst_dir  = user_prefix + '/lib'
    else:
        dst_dir  = env.get('BUILD_DIR') + '/deploy'
    action = ienv.Install(dst_dir, targets)
    if not user_prefix and str(targets[0]).endswith(env['SHLIBSUFFIX']):
        ienv.AddPostAction(action, __chrpath)
    ienv.Alias("install", action)

def __installbin(ienv, targets, name=''):
    '''
    ' Install files to system, using "scons install"
    ' If prefix is not specified, for developer convenience
    ' files are copied in relative "deploy" folder along libraries
    '''
    user_prefix = env.get('PREFIX')
    if user_prefix:
        dst_dir  = user_prefix + '/bin'
    else:
        dst_dir  = env.get('BUILD_DIR') + '/deploy'
    ienv.Alias("install", ienv.Install(dst_dir , targets))


def __installheader(ienv, targets, dir, name):
    user_prefix = env.get('PREFIX')
    if user_prefix:
        i_n = ienv.Install(user_prefix + '/include/iotivity/' + dir, targets)
    else:
        i_n = ienv.Install(env.get('BUILD_DIR') + 'deploy/include/' + dir, targets)
    ienv.Alias("install", i_n)


def __installpcfile(ienv, targets, name):
    user_prefix = env.get('PREFIX')
    if user_prefix:
        user_lib = env.get('LIB_INSTALL_DIR')
        if user_lib:
            i_n = ienv.Install(user_lib + '/pkgconfig', targets)
        else:
            i_n = ienv.Install(user_prefix + '/lib/pkgconfig', targets)
    else:
        i_n = ienv.Install(env.get('BUILD_DIR') + 'deploy/pkgconfig', targets)
    ienv.Alias("install", i_n)


def __installextra(ienv, targets, subdir="."):
    '''
    Install extra files, by default use file relative location as subdir
    or use any other prefix of your choice, or in explicit "deploy" folder
    '''
    user_lib = env.get('LIB_INSTALL_DIR')
    user_prefix = env.get('PREFIX')
    for target in targets:
        if "." == subdir:
            dst = Dir('.').srcnode().path
        else:
            dst = subdir
        if user_lib:
            dst = user_lib + '/iotivity/' + dst
        elif user_prefix:
            dst = user_prefix + '/lib/iotivity/' + dst
        else:
            dst = env.get('BUILD_DIR') + '/deploy/extra/' + dst
        i_n = ienv.Install(dst, target)
        ienv.Alias('install', i_n)


def __append_target(ienv, name, targets=None):
    if targets:
        env.Alias(name, targets)
    env.AppendUnique(TS=[name])


def __add_pthread_if_needed(ienv):
    if 'gcc' == ienv.get('CC') and target_os not in ['android']:
        ienv.AppendUnique(LINKFLAGS="-pthread")


def __print_targets(env):
    Help('''
===============================================================================
Targets:\n    ''')
    for t in env.get('TS'):
        Help(t + ' ')
    Help('''

Default: all targets will be built. You can specify the target to build:

    $ scons [options] [target]
===============================================================================
''')

# Prepare a library for use.
# Check whether it exists
#  if not try to download the source code and build it
#  if not possible, give the user a hint about downloading
# @param libname - the name of the library try to prepare
# @param lib - the lib (.so, .a etc) to check (a library may include more then
#      one lib, e.g. boost includes boost_thread, boost_system ...)
# @param path - path to build script for library. Default is <src_dir>/extlibs/<libname>/
# @param script - build script for this library. Default is SConscript
#
def __prepare_lib(ienv, libname, lib=None, path=None, script=None):
    src_dir = ienv.get('SRC_DIR')
    p_env = ienv.Clone(LIBS=[])
    if p_env.GetOption('clean') or p_env.GetOption('help'):
        return

    conf = Configure(p_env)

    if not lib:
        lib = libname
    if not conf.CheckLib(lib):
        if path:
            dir = path
        else:
            dir = os.path.join(src_dir, 'extlibs', libname)

        # Execute the script to download (if required) and build source code
        if script:
            st = dir + '/' + script
        else:
            st = dir + 'SConscript'

        if os.path.exists(st):
            SConscript(st)
        else:
            if target_os in ['linux', 'darwin', 'tizen']:
                msg = 'Library (%s) not found, please intall it, exit ...' % libname
            else:
                msg = 'Library (%s) not found and cannot find the scons script (%s), exit ...' % (
                    libname, st)
            Exit(msg)

    conf.Finish()

# Install header file(s) to <src_dir>/deps/<target_os>/include
def __install_head_file(ienv, file):
    return ienv.Install(
        os.path.join(
            src_dir, 'dep', target_os, target_arch, 'usr', 'include'), file)

# Install library binaries to <src_dir>/deps/<target_os>/lib/<arch>
def __install_lib(ienv, lib):
    return ienv.Install(
        os.path.join(
            src_dir, 'dep', target_os, target_arch, 'usr', 'lib'),
        lib)

# Run configure command (usually done before building a library)
def __configure(env, cwd, cmd):
    print("Configuring using [%s/%s] ..." % (cwd, cmd))
    # build it now (we need the shell, because some programs need it)
    with open(os.devnull, "wb") as devnull:
        handle = subprocess.Popen(cmd, shell=True, cwd=cwd, stdout=devnull)

    if handle.wait() != 0:
        raise SCons.Errors.BuildError("Run configuring script [%s]" % (cmd))

def AppendEnviroment(env):
    env.AddMethod(__set_dir, 'SetDir')
    env.AddMethod(__print_targets, 'PrintTargets')
    env.AddMethod(__src_to_obj, 'SrcToObj')
    env.AddMethod(__append_target, 'AppendTarget')
    env.AddMethod(__add_pthread_if_needed, 'AddPthreadIfNeeded')
    #env.AddMethod(__install, 'InstallTarget')
    env.AddMethod(lambda ienv, targets, name: __install(env, ienv, targets, name), 'InstallTarget')
    #env.AddMethod(installlib(env), 'UserInstallTargetLib')
    env.AddMethod(lambda ienv, targets: __installlib(env, ienv, targets), 'UserInstallTargetLib')
    env.AddMethod(__installbin, 'UserInstallTargetBin')
    env.AddMethod(__installheader, 'UserInstallTargetHeader')
    env.AddMethod(__installpcfile, 'UserInstallTargetPCFile')
    env.AddMethod(__installextra, 'UserInstallTargetExtra')
    env.AddMethod(__prepare_lib, "PrepareLib")
    env.AddMethod(__configure, "Configure")
    env.AddMethod(__install_head_file, "InstallHeadFile")
    env.AddMethod(__install_lib, "InstallLib")