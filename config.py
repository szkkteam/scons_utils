import yaml
import os
import sys
from pathlib import Path


default_yaml = \
"""
# Default configuration for the Scons Build system.
---
user_variants:
- debug:
    env_override:
    - CPPATH: "/mnt/"
    - CPPATH: "/mnt/"
    env_extension:
    - CPPATH: "/mnt/"
    - CPPATH: "/mnt/"
- release:
    env_override:
    - CPPATH: "/mnt/"
    - CPPATH: "/mnt/"
    env_extension:
    - CPPATH: "/mnt/"
    - CPPATH: "/mnt/"
default_variants:
- debug
- release
platforms:
- OS: 
  ARCH: 
  config: "/config"
- OS: 
  ARCH: 
  config: "/config"
automatic_module_discovery:
  enable: true
  scan_depth: 7
  skip_patterns:
  - ".no_recurse"
modules_list:
- driver
- driver2
- app
- example
"""

# Support function for python version < 3.5
def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def _openConfiguration(file_with_path = None):
    if file_with_path:
        fullPath = Path(filename)
        if fullPath.suffix != ".yaml" or fullPath.suffix != ".yml":
            raise FileNotFoundError ("File type: %s is not a YAML file" % (fullPath.suffix))
        else:
            try:
                with open("data.yaml", 'r') as stream:
                    data_loaded = yaml.load(stream)
            except (yaml.YAMLError, FileNotFoundError) as yaml_error:
                raise yaml_error
    else:
        try:
            data_loaded = yaml.load(default_yaml)
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
        user_config = Dict()
        # If the user provided a configuration file use it.
        if len(user_config_file) > 0:
            try:
                user_config = _openConfiguration(user_config_file)
            except yaml.YAMLError as y_error:
                msg = "Configuration file \'%s\' is damaged. Error: " % (user_config_file, y_error)
                Exit(msg)
            except FileNotFoundError as f_error:
                msg = "Configuration file \'%s\' is not exists." % (user_config_file)
                Exit(msg)

        # Overwrite the default values defined in the user config
        if sys.version_info < (3, 5):
            self._config = merge_two_dicts(def_config, user_config)
        else:
            self._config = {**def_config, **user_config}

    def GetVariantNames(self):
        return list(self._config['user_variants'].keys())

    def _getVariantEnv(self, variant_name, env):
        if 'user_variants' in self._config and variant_name in self._config['user_variants']:
            if env in  self._config['user_variants'][variant_name]:
                return self._config['user_variants'][variant_name]['env_override']
        return Dict()

    def GetVariantOverride(self, variant_name):
        return self._getVariantEnv(variant_name, 'env_override')

    def GetVariantExtension(self, variant_name):
        return self._getVariantEnv(variant_name, 'env_extension')

    def GetPlatformsDict(self):
        if 'platforms' in self._config:
            return self._config['platforms']
        else:
            return List()

    def GetModulesList(self):
        if 'modules_list' in self._config:
            return self._config['modules_list']
        else:
            return List()

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
        return List()