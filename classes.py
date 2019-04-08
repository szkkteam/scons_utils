from   SCons.Script import *
from utils import listify, path_to_key

class ILibrary(object):
    def __init__(self, name):
        super(ILibrary, self).__init__()
        self._name = name

    def __repr__(self):
        return u'%s' % (self._name)

    def GetLib(self):
        pass


class InternalLibrary(ILibrary):
    def __init__(self, name, libs=list()):
        super(InternalLibrary, self).__init__(name)
        self._libs = listify(libs) if len(libs) else [name]

    def GetLib(self):
        return self._libs, list(), list()


class ExternalLibrary(ILibrary):
    """External Library class."""

    def __init__(self, name, libs=list(), include_paths=list(), lib_paths=list()):
        """Initialize external library instance.
        @param lib_name       Symbolic name of library (or library-group)
        @param libs           Identifiers of libraries to link with
                              (if not specified, `lib_name` is used)
        @param include_paths  Additional include search paths
        @param lib_paths      Additional library search paths
        """
        super(ExternalLibrary, self).__init__(name)
        self._libs = listify(libs) if len(libs) else [name]
        self._cpp_paths = listify(include_paths)
        self._lib_paths = listify(lib_paths)

    def GetLib(self):
        return self._libs, self._cpp_paths, self._lib_paths



class LibraryList(object):

    _key_sep = '::'


    def __init__(self):
        self._libs = dict()

    def add(self,key, lib_obj, lib_deps=list()):
        assert key not in self._libs
        lib_deps = { 'lib_obj': lib_obj, 'lib_deps': listify(lib_deps) }
        self._libs[key] = lib_deps

    @classmethod
    def CreateLibraryKey(cls, module, target_name):
        """Return unique identifier for target `target_name` in `module`"""
        lib_key = '%s%s%s' % (path_to_key(module), cls._key_sep, path_to_key(target_name))
        return lib_key

    @classmethod
    def IsLibraryKey(cls, str_to_check):
        """Return True if `str_to_check` is a library identifier string"""

        return cls._key_sep in str_to_check


    def GetLibraries(self, libs):
        # Create an empty dictionary for the libs
        libs_dict = { 'CPPPATH' : list(), 'LIBS' : list(), 'LIBPATH' : list() }
        self._get_lib_depends(libs_dict, libs)

        return libs_dict


    def _get_lib_depends(self,lib_dict, lib_list):
        for lib_name in listify(lib_list):
            lib_keys = listify(self._get_matching_lib_keys(lib_name))
            if len(lib_keys) == 1:
                # Matched internal library
                lib_key = lib_keys[0]
                # Search for the found library dependencies
                libs, cpp_paths, lib_paths = self._libs[lib_key]['lib_obj'].GetLib()
                lib_dict['CPPPATH'].extend(cpp_paths)
                lib_dict['LIBS'].extend(libs)
                lib_dict['LIBPATH'].extend(lib_paths)

                # Get the dependencies
                self._get_lib_depends(lib_dict, self._libs[lib_key]['lib_deps'])
            elif len(lib_keys) > 1:
                # Matched multiple internal libraries - probably bad!
                msg = "Library identifier \'%s\' matched %d libraries (%s). Please use a fully qualified identifier instead!" % (lib_name, len(lib_keys), ', '.join(lib_keys))
                Exit(msg)
            else:  # empty lib_keys
                msg = "Library identifier \'%s\' didn\'t match any library. Is it a typo?" % (lib_name)
                Exit(msg)

    def _get_matching_lib_keys(self, lib_query):
        """Return list of library keys for given library name query.
        A "library query" is either a fully-qualified "Module::LibName" string
         or just a "LibName".
        If just "LibName" form, return all matches from all modules.
        """
        if LibraryList.IsLibraryKey(lib_query):
            # It's a fully-qualified "Module::LibName" query
            if lib_query in self._libs:
                # Got it. We're done.
                return [lib_query]
        else:
            # It's a target-name-only query. Search for matching lib keys.
            #lib_key_suffix = '%s%s' % (self._key_sep, lib_query)
            return [lib_key for lib_key in self._libs
                    if lib_key.endswith(lib_query)]