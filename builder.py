

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
from enviroment import QEnvironment, listify, remove_redundant

print("Processing using SCons version " + SCons.__version__)
print('Python '+ sys.version.replace('\n','') + ' on '+sys.platform)

def modules():
    """Generate modules to build.
    Each module is a directory with a SConscript file.
    Modules must be yielded in order of dependence,
     such that modules[i] does not depend on modules[j] for every i<j.
    """
    yield 'driver2'
    yield 'driver'
    yield 'app'

def nop(*args, **kwargs):  # pylint: disable=unused-argument
    """Take arbitrary args and kwargs and do absolutely nothing!"""
    pass

def path_to_key(path):
    """Convert path to `key`, by replacing pathseps with periods."""
    return path.replace('/', '.').replace('\\', '.')

class Builder(object):

    class TargetBuilder(object):

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
            self._shared_libs = dict()
            # Install headers dictionary
            self._shared_headers = defaultdict(list)
            # Initialize programs dictionary
            self._target_nodes = defaultdict(list)

            self._orgin_env = env

            self._env = env.Clone()
            #self._progs = defaultdict(list)
            self._env.ApplyVariant(target)

            self._target = target

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

        def Build(self):
            """Build flavor using two-pass strategy."""
            # First pass over all modules - process and collect library targets
            for module in modules():
                # Verify the SConscript file exists
                sconscript_path = os.path.join(module, 'SConscript')
                if not os.path.isfile(sconscript_path):
                    msg = "\nMissing SConscript file for module %s." % (module)
                    Exit(msg)
                print ("scons: |- First pass: Reading module %s ..." % (module))
                shortcuts = dict(
                    CreateDefaultTargetLib       = lambda lib_name, module_version, sources, headers, *args, **kwargs: self._build_alias_lib(module, lib_name, module, module_version, sources, headers, *args, **kwargs),
                    CreateTargetLib              = lambda alias, lib_name, module_version, sources, headers, *args, **kwargs: self._build_alias_lib(alias, lib_name, module, module_version, sources, headers, *args, **kwargs),
                    #StaticLib = self._lib_wrapper(self.env.StaticLibrary, module),
                    #SharedLib = self._lib_wrapper(self.env.SharedLibrary, module),
                    CreateDefaultTargetExecutable      =  nop,
                )
                self.env.SConscript(
                    sconscript_path,
                    variant_dir=os.path.join(self.env['LIB_PATH'], module),
                    #variant_dir=self.env['LIBPATH'],
                    must_exist = 1,
                    duplicate=0,
                    exports=shortcuts)
            # Second pass over all modules - process program targets
            shortcuts = dict()
            for nop_shortcut in ('CreateDefaultTargetLib', 'CreateTargetLib', 'StaticLib', 'SharedLib'):
                shortcuts[nop_shortcut] = nop
            for module in modules():
                print("scons: |- Second pass: Reading module %s ..." % (module))
                shortcuts['CreateDefaultTargetExecutable'] = lambda prog_name, prog_version, sources, link_libs, *args, **kwargs: self._build_alias_executable(module, prog_name, module, prog_version, sources, link_libs,
                                            *args, **kwargs)

                self.env.SConscript(
                    os.path.join(module, 'SConscript'),
                    variant_dir = os.path.join(self.env['BUILD_DIR'], module),
                    must_exist=1,
                    duplicate=0,
                    exports = shortcuts)

            for alias, nodes in self._target_nodes.items():
                for node in nodes:
                    #print("Target: %s - Alias: %s - Node: %s" % (self._target, alias, node))
                    self.env.Alias(alias, node)

        def _build_alias_lib(self, alias, lib_name, module_name, module_version,  sources, headers, *args, **kwargs):
            # Create unique library key from module and library name
            # TODO: Append the module version to the key, modifiy the querry to be able to search for specific version, or latest version (dont care version)
            lib_key = self.lib_key(module_name, lib_name)
            assert lib_key not in self._shared_libs
            # Store resulting library node in shared dictionary
            # self._shared_libs[lib_key] = bldr_func(lib_name, sources, *args, **kwargs)
            obj_targets = self._build_default_objects(module_name, sources)

            lib_node = self.env.Library(target=lib_name,
                                 source=obj_targets,
                                 *args, **kwargs)

            self._shared_libs[lib_key] = lib_node

            # Make sure headers are list
            headers = listify(headers)

            # Get the isntall directory for the active variant
            inc_path = self.env['INC_DIR'] + '/'

            # Install every header file to the shared <INC_DIR> keep the folder hierarchy for the header files
            inc_node = [self.env.Install(self.createNode([os.path.split(inc_path + h)[0]]), h) for h in headers]

            self._target_nodes[alias].extend(inc_node)
            self._target_nodes[alias].extend(lib_node)
            self._target_nodes['install'].extend(inc_node)

            # TODO: collect the output into aliases and register them at the end as: "install"


        def _build_default_objects(self, module, sources):
            sources = remove_redundant(sources)
            obj_path = self.env['OBJ_PATH'] + '/' + module + '/'
            # TODO: Object files maybe should placed into $OBJ_DIR/module/path/src.o. Now it will be just placed to: $OBJ_DIR/module/src.o
            # This version will be a problem, if the same src file name exists within the module.
            #obj_targets = [ self.env.Object(target = obj_path + os.path.splitext(os.path.basename(item))[0], source = item) for item in sources]
            #self.env.Alias(module, obj_targets)

            obj_targets = []
            for item in sources:
                # '#' sign here is mandatory, otherwise the include path is wrong
                # TODO: Why this is not working without the '#' sign?
                inc_dir = [self.createNode(['#' + module])] + [self.createNode([self.env['CPPPATH']])]
                base_item = os.path.splitext(os.path.basename(item))[0]  # strip relative path part and extension
                obj_node = self.env.Object(target = obj_path + base_item,
                                           source = item,
                                           CPPPATH=inc_dir)
                obj_targets.append(obj_node)
                self.env.Alias(module + '/' + item, obj_node)

            return obj_targets

        def _build_alias_executable(self, alias, prog_name, module_name, prog_version, sources, link_libs, *args, **kwargs):
            lib_nodes = []
            for lib_name in listify(link_libs):
                lib_keys = listify(self._get_matching_lib_keys(lib_name))
                if len(lib_keys) == 1:
                    # Matched internal library
                    lib_key = lib_keys[0]
                    # Extend prog sources with library nodes
                    lib_nodes.extend(self._shared_libs[lib_key])
                elif len(lib_keys) > 1:
                    # Matched multiple internal libraries - probably bad!
                    msg = "Library identifier \'%s\' matched %d libraries (%s). Please use a fully qualified identifier instead!" % (lib_name, len(lib_keys), ', '.join(lib_keys))
                    Exit(msg)
                else:  # empty lib_keys

                    msg = "Library identifier \'%s\' didn\'t match any library. Is it a typo?" % (lib_name)
                    Exit(msg)
            exec_path = self.env['BUILD_DIR'] + '/'
            obj_nodes = (self._build_default_objects(module_name, sources))
            prog_nodes = self.env.Program(exec_path + prog_name, obj_nodes, LIBS=lib_nodes, *args, **kwargs)


            #obj_targets = self._build_default_objects(module_name, sources)


        def _get_matching_lib_keys(self, lib_query):
            """Return list of library keys for given library name query.
            A "library query" is either a fully-qualified "Module::LibName" string
             or just a "LibName".
            If just "LibName" form, return all matches from all modules.
            """
            if self.is_lib_key(lib_query):
                # It's a fully-qualified "Module::LibName" query
                if lib_query in self._shared_libs:
                    # Got it. We're done.
                    return [lib_query]
            else:
                # It's a target-name-only query. Search for matching lib keys.
                lib_key_suffix = '%s%s' % (self._key_sep, lib_query)
                return [lib_key for lib_key in self._shared_libs
                        if lib_key.endswith(lib_key_suffix)]


    def __init__(self, env=None):

        # Get the default enviroment
        if env:
            self._env = env
        else:
            self._env = QEnvironment()


    def Build(self, target=None):
        if not target:
            for target in self._env.targets:
                self.Build(target)
        else:
            # Create construction env clone for flavor customizations
            target_build = Builder.TargetBuilder(self._env, target)
            target_build.Build()
