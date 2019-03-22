# scons_utils
Small utility library and standardized build environment for my own projects.

# Sequence:
- git clone bash_repo
- git clone scons_utils

. bash_repo/_bash_init.sh
. bash_repo/_set_env.sh <Build platform>

# Add the scons_util folder to the path.

run_scons <scons_utils> ? Is it really needed?

run_scons <Project folder which contains a SconsList.txt file> <Other build options>
- If the user want to build the main application, all the dependencies will be build first, and then the main app.
- For example:
   - App : Driver1 : HAL, App : Driver2 : HAL, App : Driver3
   - Build: HAL - As library
   - Build: Driver 1 - As library
   - Build: Driver 2 - As library
   - Build: Driver 3 - As library
   - Build: App - as executable
   

- git clone bash_repo
- git clone cmake_utils

- . bash_rep/_bash_init
- . bash_repo/_set_env <>

- run_cmake cmake_utils/
- run_cmake App/
or 
- cd App/
- ./build.sh
    - run_cmake cmake_utils/
    - run_cmake App/