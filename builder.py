

##
# The main build script
#
##
import os
import sys
from collections import defaultdict
#import SCons
from   SCons.Script import *
import re
from enviroment import QEnvironment
from utils import remove_redundant, listify, path_to_key, nop, module_dirs_generator
from classes import ExternalLibrary, LibraryList, InternalLibrary

print("Processing using SCons version " + SCons.__version__)
print('Python '+ sys.version.replace('\n','') + ' on '+sys.platform)
#TODO: Enable this when neccessery to force the version
#assert sys.version_info >= (3, 5)


# List of cached modules to save processing for second call and beyond
_CACHED_MODULES = list()

def scan_modules(modules_list, max_depth, file_skip_list):
    _CACHED_MODULES = listify(modules_list)

    def modules():
        """Generate modules to build.
        Each module is a directory with a SConscript file.
        """
        if not _CACHED_MODULES:
            # Build the cache
            def build_dir_skipper(dirpath):
                """Return True if `dirpath` is the build base dir."""
                return os.path.normpath('out') == os.path.normpath(dirpath)
            def hidden_dir_skipper(dirpath):
                """Return True if `dirpath` last dir component begins with '.'"""
                last_dir = os.path.basename(dirpath)
                return last_dir.startswith('.')
            for module_path in module_dirs_generator(
                    max_depth=max_depth, followlinks=False,
                    dir_skip_list=[build_dir_skipper, hidden_dir_skipper],
                    file_skip_list=file_skip_list):
                _CACHED_MODULES.append(module_path)
        # Yield modules from cache
        for module in _CACHED_MODULES:
            yield module

    return modules

class ProjectBuilder(object):
    def __init__(self, env=None):
        #pydevd.settrace()
        # Get the enviroment
        if env:
            self._env = env
        else:
            self._env = QEnvironment()

        scan_depth = self._env._config.GetAutomaticScanDepth()
        skip_keyword = self._env._config.GetAutomaticScanKeyword()
        module_list = self._env._config.GetModulesList()

        self._modules = scan_modules(module_list, scan_depth, skip_keyword)


    def Build(self, target=None):
        if not target:
            for target in self._env.targets:
                self.Build(target)
        else:
            # Create construction env clone for flavor customizations
            target_build = _targetBuilder(self._env, target)
            target_build.Build(self._modules)



class _targetBuilder(object):

    _key_sep = '::'

    @classmethod
    def lib_key(cls, module, target_name):
        """Return unique identifier for target `target_name` in `module`"""
        return '%s%s%s' % (path_to_key(module), cls._key_sep,
                           path_to_key(target_name))

    @classmethod
    def is_lib_key(cls, str_to_check):
        """Return True if `str_to_check` is a library identifier string"""

        return cls._key_sep in str_to_check

    def __init__(self, env, target):
        print ("scons: Processing variant: \'%s\'..." % (target))
        # Initialize shared libraries dictionary
        self._shared_libs = LibraryList()

        # Install headers dictionary
        self._shared_headers = defaultdict(list)
        # Initialize programs dictionary
        self._target_nodes = defaultdict(list)

        self._orgin_env = env

        self._env = env.Clone()
        #self._progs = defaultdict(list)
        self._env.ApplyVariant(target)

        self._target = target

        # Load the external libraries
        for lib in self._env._config.GetExternalLibraries():
            ext_lib = self._env._config.GetExternalLib(lib)
            self._shared_libs.add(ext_lib._name, ext_lib)

    ##
    # Creates a path out of given elements, which are substituted if needed.
    # To avoid hard coded paths and to allow latest possible substitution of environment variables, each path used should be created by the same method.
    # Initially the path to be created is set empty.
    # Each path element is checked for special characters and handled accordingly.
    # If no path elements are given, i.e. the 'pathelems' list is empty, the empty path is returned.
    # If the first character of the current path element is '$', the remaining characters represent an environment variable by convention.
    # For example, if the current path element is '$BINDIR', it is substituted by env['BINDIR'] and appended to the path to be created.
    # If the first character of the current path element is '/' on POSIX OSs and '\' on win32 OSs, the path to be created is replaced by the current path element.
    # For example, if the path to be created is 'local/bin' and the current path element is '/usr/local/bin' then the path to be created becomes '/usr/local/bin'.
    #
    # @param pathelems list of path elements to be composed to path (default: [])
    # @param env the environment to use (default: environment)
    #
    def createPath(self, pathelems=[]):
        path = ''
        for pathelem in pathelems:
            if pathelem and pathelem[0] == '$':
                elem = self.env[pathelem[1:]]
            else:
                elem = pathelem
            if elem and elem[0] == os.sep:
                path = elem
            else:
                path = os.path.join(path, elem)
        return path

        ##

    # Creates a node out of path, which is composed out of given path elements.
    #
    # The path is created by calling 'createPath' method with given path elements.
    # If the returned path is empty, no node is created, instead None is returned.
    # If 'type' parameter is 'dir', a directory node is created from path.
    # Else a file  node is created from path.
    #
    # @param pathelems list of path elements to be composed to path, of which a node is created (default: [])
    # @param type the type of node to create (default: 'dir')
    # @param env the environment to use (default: environment)
    #
    def createNode(self, pathelems=[], type='dir'):
        node = None
        path = self.createPath(pathelems=pathelems)
        if path:
            if type == 'dir':
                node = self.env.Dir(path)
            else:
                node = self.env.File(path)
        return node

    @property
    def env(self):
        return self._env._env

    def createAlias(self, name, node):
        self._target_nodes[name].extend(node)

    def first_pass_dict(self, module):
        _default_shortcuts = dict(
            CreateDefaultTargetLib=lambda name=module, version='0.1', sources=list(), headers=list(), libs=list(), *args,
            **kwargs: self._build_alias_lib(
                module, name, module, version, sources, headers, libs, *args, **kwargs),
            CreateTargetLib=lambda target=self._target, name=module, version='0.1', sources=list(), headers=list(), libs=list(),
            *args, **kwargs: self._build_alias_lib(
                target, name, module, version, sources, headers, libs, *args, **kwargs),
            CreateDefaultTargetExecutable=nop,
            CreateTargetExecutable=nop
        )
        return _default_shortcuts

    def second_pass_dict(self, module):
        _default_shortcuts = dict(
            CreateDefaultTargetLib=nop,
            CreateTargetLib=nop,
            CreateDefaultTargetExecutable=lambda name=module, version='0.1', sources=list(), headers=list(),
            libs=list(), *args, **kwargs: self._build_alias_executable(
                self._target, name, module, version, sources, libs, *args, **kwargs),
            CreateTargetExecutable=lambda target=self._target, name=module, version='0.1', sources=list(),
            headers=list(), libs=list(), *args, **kwargs: self._build_alias_executable(
                target, name, module, version, sources, libs, *args, **kwargs)
        )
        return _default_shortcuts

    def Build(self, modules):
        """Build flavor using two-pass strategy."""
        # First pass over all modules - process and collect library targets
        for module in modules():
            # Verify the SConscript file exists
            sconscript_path = os.path.join(module, 'SConscript')
            if not os.path.isfile(sconscript_path):
                msg = "\nMissing SConscript file for module %s." % (module)
                Exit(msg)
            print ("scons: |- First pass: Reading module %s ..." % (module))
            # Workaround to do not let the system to start app build, until the libs are not scanned.
            self.env.SConscript(
                sconscript_path,
                variant_dir=os.path.join(self.env['LIB_PATH'], module),
                must_exist=1,
                duplicate=0,
                exports=self.first_pass_dict(module))
        # Second pass over all modules - process program targets
        # Workaround to do not let the system to build the libs twice
        for module in modules():
            print("scons: |- Second pass: Reading module %s ..." % (module))
            self.env.SConscript(
                os.path.join(module, 'SConscript'),
                variant_dir=os.path.join(self.env['BUILD_DIR'], module),
                must_exist=1,
                duplicate=0,
                exports=self.second_pass_dict(module))

        # Create aliases for each node
        for alias, nodes in self._target_nodes.items():
            for node in nodes:
                #print("Target: %s - Alias: %s - Node: %s" % (self._target, alias, node))
                self.env.Alias(alias, node)

    def _build_default_objects(self, module, sources):
        # Make sure headers are list
        sources = listify(sources)
        # Remove redundant elements
        sources = remove_redundant(sources)
        obj_targets = []
        if len(sources) > 0:
            obj_path = self.env['OBJ_PATH'] + '/' + module + '/'
            # TODO: Object files maybe should placed into $OBJ_DIR/module/path/src.o. Now it will be just placed to: $OBJ_DIR/module/src.o
            for item in sources:
                # '#' sign here is mandatory, otherwise the include path is wrong
                # TODO: Why this is not working without the '#' sign?
                # Create a node from the include directory
                inc_dir = [self.createNode(['#' + module])] + [self.createNode([self.env['CPPPATH']])]
                # Get the base fileanem from the hive source
                base_item = os.path.splitext(os.path.basename(item))[0]  # strip relative path part and extension
                # TODO: Cannot create nodes from item,s Why?
                obj_node = self.env.Object(
                                target=obj_path + base_item,
                                source=item,
                                CPPPATH=inc_dir)
                # Append the object node to targets
                obj_targets.append(obj_node)
                # Create an alias target from object node
                self.createAlias(module + '/' + item, obj_node)
        return obj_targets

    def _build_alias_lib(self, alias, lib_name, module_name, module_version,  sources, headers, libs, *args, **kwargs):
        # TODO: Append the module version to the key, modifiy the querry to be able to search for specific version, or latest version (dont care version)
        # Store resulting library node in shared dictionary
        obj_targets = self._build_default_objects(module_name, sources)
        # Create a lib node.
        lib_node = self.env.Library(target=lib_name, source=obj_targets, *args, **kwargs)
        # Create unique library key from module and library name
        key = LibraryList.CreateLibraryKey(module_name, lib_name)
        # Store the library key in shared libs list
        self._shared_libs.add(key, InternalLibrary(lib_name, lib_node), libs)

        # Create an alias target for the lib
        self.createAlias(alias, lib_node)
        # Make sure headers are list
        headers = listify(headers)
        if len(headers) > 0:
            # Remove redundant elements
            headers = remove_redundant(headers)
            # Get the isntall directory for the active variant
            inc_path = self.env['INC_DIR'] + '/'
            # Install every header file to the shared <INC_DIR> keep the folder hierarchy for the header files
            inc_node = [self.env.Install(self.createNode([os.path.split(inc_path + h)[0]]), h) for h in headers]
            # Create alias targets for the header nodes
            self.createAlias(alias, inc_node)
            self.createAlias('install', inc_node)

    def _build_alias_executable(self, alias, prog_name, module_name, prog_version, sources, link_libs, *args, **kwargs):
        lib_nodes = []
        # Store the kwarg flags
        cpp_paths = listify(kwargs.pop('CPPPATH', list()))
        ext_libs = listify(kwargs.pop('LIBS', list()))
        lib_paths = listify(kwargs.pop('LIBPATH', list()))

        # Get the dependencies for the executable
        libs_dict = self._shared_libs.GetLibraries(link_libs)

        # Extend the stored flags with the lib dependencies
        cpp_paths.extend(libs_dict['CPPPATH'])
        ext_libs.extend(libs_dict['LIBS'])
        lib_paths.extend(libs_dict['LIBPATH'])

        # Copy back the dependencies to the kwargs
        kwargs['CPPPATH'] = cpp_paths
        kwargs['LIBS'] = ext_libs
        kwargs['LIBPATH'] = lib_paths

        exec_path = self.env['BUILD_DIR'] + '/'
        obj_nodes = (self._build_default_objects(module_name, sources))
        prog_nodes = self.env.Program(exec_path + prog_name, obj_nodes, **kwargs)
        # Create an alias target for the lib
        #if self._target in BUILD_TARGETS:
        self.createAlias(alias, prog_nodes)
        self.createAlias(module_name, prog_nodes)

