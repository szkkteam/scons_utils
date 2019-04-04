import yaml
import os
import sys
import exceptions

default_config = \
"""
---
user_variants:
  debug:
    env_override: {}
    env_extension: {}
  release:
    env_override: {}
    env_extension: {}
default_variants:
- debug
- release
platforms: []
automatic_module_discovery:
  enable: true
  scan_depth: 7
  skip_patterns: []
modules_list: []
"""


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
    return merge(x,y)
    #z = x.copy()   # start with x's keys and values
    #z.update(y)    # modifies z with y's keys and values & returns None
    #return z


def _openConfiguration(file_with_path=None):
    if file_with_path:
        norm_path = os.path.normpath(file_with_path)
        extension = os.path.splitext(norm_path)[1]
        if not (extension == ".yaml" or extension == ".yml"):
            raise RuntimeError ("File type: %s is not a YAML file" % (norm_path))
            pass
        else:
            try:
                with open(norm_path, 'r') as stream:
                    data_loaded = yaml.load(stream)
            #except (yaml.YAMLError, FileNotFoundError) as yaml_error:
            except Exception as yaml_error:
                raise yaml_error
    else:
        try:
            data_loaded = yaml.load(default_config)
        except yaml.YAMLError as yaml_error:
            raise yaml_error
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
                msg = "Configuration file \'%s\' cannot be loaded. Error: " % (user_config_file, y_error)
                Exit(msg)
        #print ("def_config: ", def_config)
        #print ("user_config: ", user_config)
        # Overwrite the default values defined in the user config
        print("Default dict: \n", def_config)
        import pydevd
        pydevd.settrace()
        self._config = merge_two_dicts(def_config, user_config)
        print("Merged dict: \n", self._config)

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

    def GetPlatformsDict(self):
        if 'platforms' in self._config:
            return self._config['platforms']
        else:
            return list()

    def GetModulesList(self):
        if 'modules_list' in self._config:
            return self._config['modules_list']
        else:
            return list()

    def IsAutomaticScanUsed(self):
        if len (self.GetModulesList()) == 0:
            if 'automatic_module_discovery' in self._config and 'enable' in self._config['automatic_module_discovery']:
                return self._config['automatic_module_discovery']['enable']
        return False

    def GetAutomaticScanDepth(self):
        if 'automatic_module_discovery' in self._config and 'scan_depth' in self._config['automatic_module_discovery']:
            return self._config['automatic_module_discovery']['scan_depth']
        return "1"

    def GetAutomaticScanKeyword(self):
        if 'automatic_module_discovery' in self._config and 'skip_patterns' in self._config['automatic_module_discovery']:
            return self._config['automatic_module_discovery']['skip_patterns']
        return list()