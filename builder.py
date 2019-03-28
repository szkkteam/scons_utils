

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

def get_targets(env, *args, **kwargs):
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
        # Remove matched target names to avoid scanning them again
        target_names = target_names.difference(matching_target_names)
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
