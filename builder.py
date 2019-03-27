

##
# The main build script
#
##
import os
import sys
import SCons

#from enviroment import *
from options import InitializeCommandLineOptions
from enviroment import GetTargetOs, GetTargetArch, GetDefaultEnvironment

print("Processing using SCons version " + SCons.__version__)
print('Python '+ sys.version.replace('\n','') + ' on '+sys.platform)

project_version = '0.1.0'

help_vars = InitializeCommandLineOptions(project_version)

# Workaround to don't let scons randomly create this dblite file.
#env.SConsignFile(os.path.join(env.Dir('#').abspath, project_path, '.sconsign.dblite'))

env = GetDefaultEnvironment(help_vars)

#print ("CC:", env['CC'])
print ("Project version: ", env.get('PROJECT_VERSION'))

#env.Program(target = 'main', source = ['main.c'])
env.Program('main.c')

# Load common build config
#SConscript('platforms/platform.sci', must_exist=1)