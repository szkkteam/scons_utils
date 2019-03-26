##
# This script includes generic build options:
#    release/debug, target os, target arch, cross toolchain, build environment etc
##
import os
import sys
import platform
import re
#import SCons.Variables
from   SCons.Script import *

######################################################################
# Common build options
######################################################################

def InitializeCommandLineOptions(project_version):
    help_vars = Variables()
    help_vars.AddVariables(
        ('PROJECT_VERSION',
                     'The version of Scons Utils',
                     project_version),
     )
     
    return help_vars