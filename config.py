import os
import sys
import copy
from SCons.Script import *
from utils import remove_redundant, listify
from classes import ExternalLibrary

default_config = {'automatic_module_discovery': { 'scan_depth': 7,
                                'skip_patterns': []},
 'default_variants': ['debug', 'release'],
 'external_libs': {},
 'modules_list': [],
 'platforms': {'linux': {'arch': ['x86', 'x86_64', 'arm', 'armv7l', 'arm-v7a', 'armeabi-v7a', 'arm64', 'mips', 'mipsel',
                                  'mips64', 'mips64el', 'i386', 'powerpc', 'sparc', 'aarch64', 'armv6l', 'armv7l'],
                         'config': '/platforms/linux/SConscript',
                         'hosts': ['linux']},
               'windows': {'arch': ['x86', 'amd64', 'arm'],
                         'config': '/platforms/windows/SConscript',
                         'hosts': ['windows']}},
 'user_variants': {'debug': {'env_extension': {}, 'env_override': {}},
                   'release': {'env_extension': {}, 'env_override': {}}}}


def data_merge(a, b):
    """merges b into a and return merged result

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen"""
    key = None
    # ## debug output
    # sys.stderr.write("DEBUG: %s to %s\n" %(b,a))
    try:
        if a is None or isinstance(a, str) or isinstance(a, int) or isinstance(a, float):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
                if a != None:
                    a = remove_redundant(a)
            else:
                # append to list
                a.append(b)
                if a != None:
                    a = remove_redundant(a)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = data_merge(a[key], b[key])
                    else:
                        a[key] = b[key]
            else:
                print('Cannot merge non-dict "%s" into dict "%s"' % (b, a))
        else:
            print('NOT IMPLEMENTED "%s" into "%s"' % (b, a))
    except TypeError as e:
        print('TypeError "%s" in key "%s" when merging "%s" into "%s"' % (e, key, b, a))
    return a

def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a

# Support function for python version < 3.5
def merge_two_dicts(x, y):
    return data_merge(x,y)
    #z = x.copy()   # start with x's keys and values
    #return data_merge(z, y)    # modifies z with y's keys and values & returns None



def _openYamlConfig(file):
    try:
        import yaml
    except ImportError:
        raise
    else:
        try:
            with open(file, 'r') as stream:
                data_loaded = yaml.load(stream)
        except Exception as yaml_error:
            raise yaml_error
        else:
            return data_loaded

def _openJsonConfig(file):
    try:
        import json
    except ImportError:
        raise
    else:
        try:
            with open(file, 'r') as stream:
                data_loaded = json.load(stream)
        except Exception as json_error:
            raise json_error
        else:
            return data_loaded


def _openConfiguration(file_with_path=None):
    if file_with_path:
        norm_path = os.path.normpath(file_with_path)
        extension = os.path.splitext(norm_path)[1]
        accepted_extensions = ['.yaml', '.yml', '.json']

        if extension not in accepted_extensions:
            raise RuntimeError ("File type: %s is not a YAML or JSON file" % (norm_path))
        else:
            if extension == '.json':
                data_loaded = _openJsonConfig(norm_path)
            else:
                data_loaded = _openYamlConfig(norm_path)
    else:
        data_loaded = copy.deepcopy(default_config)
    return data_loaded


class BuildConfig(object):
    def __init__(self, user_config_file = ""):
        # Load the default configuration file
        try:
            def_config = _openConfiguration()
        except yaml.YAMLError as y_error:
            msg = "Default configuration is damaged. Error: " % (y_error)
            Exit(msg)
        # Create an empty dictionary for the user config
        user_config = dict()
        # If the user provided a configuration file use it.
        if len(user_config_file) > 0:
            try:
                user_config = _openConfiguration(user_config_file)
            except Exception as y_error:
                msg = "Configuration file \'%s\' cannot be loaded. Error: %s" % (user_config_file, y_error)
                Exit(msg)
        #print ("def_config: ", def_config)
        #print ("user_config: ", user_config)
        # Overwrite the default values defined in the user config
        #print("Default dict: \n", def_config)
        #TODO: Valide the user config file.
        self._config = merge_two_dicts(def_config, user_config)
        #print("Merged dict: \n", self._config)

    def GetVariantNames(self):
        return list(self._config['user_variants'].keys())

    def _getVariantEnv(self, variant_name, env):
        if 'user_variants' in self._config and variant_name in self._config['user_variants']:
            if env in  self._config['user_variants'][variant_name]:
                return self._config['user_variants'][variant_name][env]
        return dict()

    def GetVariantOverride(self, variant_name):
        return self._getVariantEnv(variant_name, 'env_override')

    def GetVariantExtension(self, variant_name):
        return self._getVariantEnv(variant_name, 'env_extension')

    def GetPlatforms(self):
        if 'platforms' in self._config:
            return list(self._config['platforms'].keys())
        else:
            return list()

    def GetArchitectures(self, target_os):
        if 'platforms' in self._config:
            if target_os in self._config['platforms'] and 'arch' in self._config['platforms'][target_os]:
                return self._config['platforms'][target_os]['arch']
        return list()

    def GetPlatformConfig(self, target_os):
        if 'platforms' in self._config:
            if target_os in self._config['platforms'] and 'config' in self._config['platforms'][target_os]:
                return self._config['platforms'][target_os]['config']
        return ""

    def GetHosts(self, target_os):
        if 'platforms' in self._config:
            if target_os in self._config['platforms'] and 'hosts' in self._config['platforms'][target_os]:
                return self._config['platforms'][target_os]['hosts']
        return list()

    def GetModulesList(self):
        if 'modules_list' in self._config:
            return self._config['modules_list']
        else:
            return list()

    def GetAutomaticScanDepth(self):
        if 'automatic_module_discovery' in self._config and 'scan_depth' in self._config['automatic_module_discovery']:
            return self._config['automatic_module_discovery']['scan_depth']
        return "1"

    def GetAutomaticScanKeyword(self):
        if 'automatic_module_discovery' in self._config and 'skip_patterns' in self._config['automatic_module_discovery']:
            return self._config['automatic_module_discovery']['skip_patterns']
        return list()

    def GetExternalLibraries(self):
        return list(self._config['external_libs'].keys())

    def GetExternalLib(self, lib_name):
        if 'external_libs' in self._config:
            if lib_name in self._config['external_libs']:
                libs = self._config['external_libs'][lib_name]['libs']
                include_paths = self._config['external_libs'][lib_name]['include_paths']
                lib_paths = self._config['external_libs'][lib_name]['lib_paths']
                return ExternalLibrary(lib_name, libs, include_paths, lib_paths)
        return None