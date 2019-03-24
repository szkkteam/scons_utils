#!/bin/bash

############################################
#set -e

# Bash functions
############################################

SCONS_VERSION=scons-3.0.4

# Add path to path enviroment variable is not exists
pathadd() {
    newelement=${1%/}
    if [ -d "$1" ] && ! echo $PATH | grep -E -q "(^|:)$newelement($|:)" ; then
        if [ "$2" = "after" ] ; then
            PATH="$PATH:$newelement"
        else
            PATH="$newelement:$PATH"
        fi
    fi
}

# Remove path from enviroment variable
pathrm() {
    PATH="$(echo $PATH | sed -e "s;\(^\|:\)${1%/}\(:\|\$\);\1\2;g" -e 's;^:\|:$;;g' -e 's;::;:;g')"
}


# Get the absoluty path for the Scons_utils directory
export SCONS_UTILS_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

# Add the current directory to the PATH
#pathadd $SCONS_UTILS_PATH after 

export SCONS_PATH=$SCONS_UTILS_PATH/$SCONS_VERSION

# Add the scons main file
export SCONS_EXEC=scons.py

export SCONS_MAIN_SCU=builder.scu

# Create the build command alias
alias run_scons='$PYTHON_EXECUTABLE $SCONS_PATH/$SCONS_EXEC -f $SCONS_UTILS_PATH/$SCONS_MAIN_SCU --site-dir=$SCONS_UTILS_PATH --project_path'


# Export the new path to the system
export PATH

# Test
#echo $PATH
