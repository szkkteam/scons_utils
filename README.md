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
   
- Dependencies has to be clarified and maintained by every library. This means, for example, App is know Driver1, Driver2 and Driver3 as dependencies. Driver1 know HAL as dependencies, Driver2 know HAL as dependencies, but the build system has to check that,
if HAL is already built and the build is up-to date, then there is no need to build it again.

- Dependencies has to be tracked as git repos also. If one dependency is not present, the build system has to clone it, switch to the correct branch/commit then it need to start the build as stated above.
    for example:
    deps.json

- run_scons is an alias command. It will wrap the following: $(PYTHON_PATH)/$(PATHON_EXEC) -tt $(SCONS_PATH)/$(SCONS_EXEC) -f $(SCONS_UTILS_PATH)/main.scu --site-dir=$(SCONS_UTILS_PATH) --project_path=
- running this command will looks like this: run_scons App/ which is actually translated to :
$(PYTHON_PATH)/$(PATHON_EXEC) -tt $(SCONS_PATH)/$(SCONS_EXEC) -f $(SCONS_UTILS_PATH)/main.scu --site-dir=$(SCONS_UTILS_PATH) --project_path=App/
   

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