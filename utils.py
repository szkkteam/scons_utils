import os
import sys
import platform
import re
from   SCons.Script import *
#from enviroment import GetTargetOs, GetTargetArch

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
    #if len(args) != len(set(args)):
        # error_inconsistent_module_list
        #args = list(set(args))  # silently remove redundant items
    #return args
    return list(set(args))  # silently remove redundant items

def intersection(*args):
    """Return the intersection of all iterables passed."""
    args = list(args)
    result = set(listify(args.pop(0)))
    while args and result:
        # Finish the loop either when args is consumed, or result is empty
        result.intersection_update(listify(args.pop(0)))
    return result

######################################################################
# Convenience functions to "extend" SCons
######################################################################

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
    variant = env['VARIANT']

    # Create base out directory path.
    # project_root/out/<target_os>/<target_arch>/<install or bin>/
    build_dir = dir + '/out/%s_%s/%s/' % (target_os, target_arch, variant) + '%s/'
    # Create variant directory. Variants in default are: <release, debug> but other variants can be specified also
    # Create a binary directory
    # project_root/out/<target_os>/<target_arch>/bin/
    bin_dir = build_dir % 'bin'
    # Create a static/shared library directory
    # project_root/out/<target_os>/<target_arch>/install/<variant>
    lib_dir = build_dir % 'install'
    # Create an include directory
    # project_root/out/<target_os>/<target_arch>/install/include/
    #inc_dir = (build_dir + '/include/') % 'install'
    inc_dir = (build_dir) % 'install'
    # Create an object directory
    # project_root/out/<target_os>/<target_arch>/bin/obj/
    obj_dir = (build_dir + '/obj/') % 'bin'

    #env.VariantDir((variant_dir % 'bin'), dir, duplicate=0)

    env.Replace(BUILD_DIR=(bin_dir))
    env.Replace(SRC_DIR=dir)
    env.Replace(INC_DIR=(inc_dir))
    env.Replace(LIB_PATH=(lib_dir))
    env.Replace(OBJ_PATH=(obj_dir))


    env.Replace(CPPPATH=inc_dir)


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

def __get_targets(env, *args, **kwargs):
    """Return list of target nodes for given target name queries.
    Every positional argument is a singe query.
    Supported query formats:
    1. Fully-Qualified "Module::Target" name queries.
       Matches exact target entries.
    2. Target-name-only queries (no "::" in query).
       Matches all targets with that name, potentially from multiple modules.
       In case of multi-module matches, a warning will be printed.
    3. Wildcard queries (containing "*" in the query).
       Matches all targets whose fully-qualified Module::Target name
       matches the wildcard expression.
       No warning is printed for multiple matches.
    Optionally, pass a keyword argument "no_multi_warn=True" to suppress
    warning messages for unexpected multiple matches for a query.
    Warning messages are always printed when a query results zero matches.
    """
    no_multi_warn = kwargs.pop('no_multi_warn', False)
    def query_to_regex(query):
        """Return RegEx for specified query `query`."""
        # Escape query string
        print ("query", query)
        query = re.escape(query)
        if r'\*' in query:  # '\' because of RE escaping
            # It's a wildcard query
            return re.compile('^%s$' % (query.replace('\\*', '.*'))), False
        if r'\:\:' in query:  # '\' because of RE escaping
            # It's a fully-qualified "Module::Target" query
            return re.compile('^%s$' % (query)), True
        # else - it's a target-name-only query
        return re.compile(r'^[^\:]*\:{2}%s$' % (query)), True

    target_names = set(env['targets'].keys())
    matching_target_names = list()
    for query in args:
        print("args: ", args)
        # Remove matched target names to avoid scanning them again
        target_names = target_names.difference(matching_target_names)
        print("target_names: ", target_names)
        qre, warn = query_to_regex(query)
        match_count = 0
        for target_name in target_names:
            if qre.match(target_name):
                matching_target_names.append(target_name)
                match_count += 1
        # Warn about unexpected scenarios
        if 0 == match_count:
            # No matches for query probably means typo in query
            print ('scons: warning: get_targets query "%s" had no matches' %
                   (query))
        elif warn and (not no_multi_warn) and (1 < match_count):
            # Multiple matches for a "warnable" query might indicate
            #  a too-broad query.
            print ('scons: warning: get_targets query "%s" had %d matches' %
                   (query, match_count))
    # Aggregate all matching target lists and return a single list of targets
    return reduce(lambda acculist, tname: acculist + env['targets'][tname],
    matching_target_names, [])

def AppendEnviroment(env):
    env.AddMethod(__set_dir, 'SetDir')
    #TODO: Lambda is not working, with AddMethod. Neither decoatros, so need to think how to fix this.
    #env.AddMethod(lambda *args, **kwargs: __get_targets(env, *args, **kwargs), 'LinkWith')
    env.LinkWith = lambda *args, **kwargs: __get_targets(env, *args, **kwargs)

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