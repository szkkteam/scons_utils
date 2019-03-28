

##
# The main build script
#
##
import os
import sys
#import SCons
from   SCons.Script import *
import re
from options import InitializeCommandLineOptions
from enviroment import GetTargetOs, GetTargetArch, GetDefaultEnvironment

def intersection(*args):
    """Return the intersection of all iterables passed."""
    args = list(args)
    result = set(listify(args.pop(0)))
    while args and result:
        # Finish the loop either when args is consumed, or result is empty
        result.intersection_update(listify(args.pop(0)))
    return result

def nop(*args, **kwargs):  # pylint: disable=unused-argument
    """Take arbitrary args and kwargs and do absolutely nothing!"""
    pass

BASE_TARGET_ENV_EXTENSIONS = {
    'debug': dict(
        # Extra flags for debug builds
    ),
    'release': dict(
        # Extra flags for release builds
    ),
}

def targets(target_list):
    if target_list:
        target_lists = set(BASE_TARGET_ENV_EXTENSIONS.keys() + target_list.keys())
    else:
        target_lists = set(BASE_TARGET_ENV_EXTENSIONS.keys())
    for target in target_lists:
        # Skip "hidden" records
        yield flavor

class Builder(object):
    def __init__(self, target, target_list=None):
        # Get the command line variables
        help_vars = InitializeCommandLineOptions(project_version)
        # Initialize shared libraries dictionary
        self._shared_libs = dict()
        # Get the default enviroment
        self._def_env = GetDefaultEnvironment(help_vars)
        # Get the command line target
        self._getCommandLineTarget(target_list)
        # Set the selected target
        if target_list:
            self._target_list = set(BASE_TARGET_ENV_EXTENSIONS.keys() + target_list.keys())
        else:
            self._target_list = set(BASE_TARGET_ENV_EXTENSIONS.keys())
        # Apply target env customizations
        if target in self._target_list:
            self._env.Append(**self._target_list[target])
        # Support using the flavor name as target name for its related targets
        #TODO: Check buildroot? Or use env['BUILD_DIR']
        self._env.Alias(flavor, '$BUILDROOT')

    def _getCommandLineTarget(self, target_list):
        # If a target is activated in the external environment - use it
        if 'BUILD_TARGET' in os.environ:
            active_target = os.environ['BUILD_TARGET']
            if not active_target in targets(target_list):
                msg = "\nError: %s (from env) is not a known target." % (active_target)
                Exit(msg)
            print ('scons: Using active target "%s" from your environment' % (active_target))
            self._env.activeTargets = [active_target]
        else:
            # If specific flavor target specified, skip processing other flavors
            # Otherwise, include all known flavors
            self._env.activeTargets = (set(targets(target_list)).intersection(COMMAND_LINE_TARGETS)  # pylint: disable=undefined-variable
                           or targets(target_list))

def modules():
    """Generate modules to build.
    Each module is a directory with a SConscript file.
    Modules must be yielded in order of dependence,
     such that modules[i] does not depend on modules[j] for every i<j.
    """
    yield 'driver'
    yield 'app'


print("Processing using SCons version " + SCons.__version__)
print('Python '+ sys.version.replace('\n','') + ' on '+sys.platform)

project_version = '0.1.0'

help_vars = InitializeCommandLineOptions(project_version)

# Workaround to don't let scons randomly create this dblite file.
#env.SConsignFile(os.path.join(env.Dir('#').abspath, project_path, '.sconsign.dblite'))

env = GetDefaultEnvironment(help_vars)



build_dir = env['BUILD_DIR']

# Allow including from project build base dir
env.AppendUnique(CPPPATH=[build_dir])
print("CPPPATH: ", env['CPPPATH'])

env['targets'] = dict()
# Allow modules to use `env.get_targets('libname1', 'libname2', ...)` as
#  a shortcut for adding targets from other modules to sources lists.
env.get_targets = lambda *args, **kwargs: get_targets(env, *args, **kwargs)

# Go over modules to build, and include their SConscript files
for module in modules():
    # Verify the SConscript file exists
    sconscript_path = os.path.join(module, 'SConscript')
    assert os.path.isfile(sconscript_path)
    print 'scons: |- Reading module', module, '...'
    # Execute the SConscript file, with variant_dir set to the
    #  module dir under the project build dir.
    targets = env.SConscript(sconscript_path,
                             variant_dir=os.path.join(build_dir, module),
                             exports={'env': env},
                             duplicate=0)

    #env.UserInstallTargetBin(targets)
    # Add the targets built by this module to the shared cross-module targets
    #  dictionary, to allow the next modules to refer to these targets easily.
    for target_name in targets:
        #env.UserInstallTargetLib(target_name)
        # Target key built from module name and target name
        # It is expected to be unique
        target_key = '%s::%s' % (module, target_name)
        assert target_key not in env['targets']
        env['targets'][target_key] = targets[target_name]
