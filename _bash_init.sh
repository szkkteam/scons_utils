#!/bin/bash

# Just a Test
############################################
STRING="_bash_init.sh"
#print variable on a screen
echo $STRING
############################################

# Get the absoluty path for the Scons_utils directory
SCRIPTS_BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

# Add the current directory to the PATH
PATH=$PATH:$SCRIPTS_BASE_DIR

# Export the new path to the system
export PATH

echo $PATH
