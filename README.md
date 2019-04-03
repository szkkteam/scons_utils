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

- run_scons is an alias command. It will wrap the following: $(PYTHON_PATH)/$(PATHON_EXEC) -tt $(SCONS_UTILS_PATH)/scons.py -f $(SCONS_UTILS_PATH)/main.scu --site-dir=$(SCONS_UTILS_PATH) --project_path=
- running this command will looks like this: run_scons App/ which is actually translated to :
$(PYTHON_PATH)/$(PATHON_EXEC) -tt $(SCONS_PATH)/$(SCONS_EXEC) -f $(SCONS_UTILS_PATH)/main.scu --site-dir=$(SCONS_UTILS_PATH) --project_path=App/


   
TODO:
- YAML config file in project root. It will override the default yaml stored in the scons utils. In the YAML the following things can be configured:
- Default variants: [debug/release/etc...] When a default target lib or exec used in a modul script, all of them will be built when the default target is selected.
- User variants. [test/example/etc...] All of this items will be added to the variants lists. If they are also present in the default section, the default variants options will be true. Overrides and extensions will present here also.
- Cross compile target config. A filename with relative path is defined here. Also OS+ARCH tags. The user can specify the OS and ARCH parameters during build, and the defined target will be added to the list. If the selected OS and ARCH is the same as the defined,
    the linked SconScript file will be used to set up the system.
- Automatic module discovery. If it's selected/defined, the system will scan the folders to determine the modules. A Max depth, and skip files can be defined here.
- List of modules. If the automatic module discovery is not defined, the list of modules will tell the system which modules shall be scanned for sconscript file. The order of modules will be top down.

build phases:
- ??? Preprocess
- #0 - Scan modules, read sconscipt, process the following functions: [Set(), ... ]
- #1 - Go through on the listed modules, build libraries, install headers, process the following functions: [Get(), CreateDefaultTargetLib(), CreateTargetLib(), ... ]
- #2 - Go through on the listed modules, build executables and link them. process the following functions: [Get(), CreateDefaultTargetExecutable(), CreateTargetExecutable(), ... ]
- ??? Postprocess 

- Automatic module discovery
- Set(DEFINE_NAME, value) -> This has to be parsed from the sconscript files in the 0. phase.
- Get(DEFINE_NAME) -> Return [None, value] it can return with the defined value, or with None, if the define is not exists. This has to be parsed from the sconsript in the phase 1.





https://www.ostricher.com/2014/09/scons-multi-module-with-build-dir/
https://bitbucket.org/scons/scons/wiki/MavenIdeasWithSCons

https://chromium.googlesource.com/native_client/src/native_client/+/202ccbd707ded4002aa402b9da0ea4e4026f3a1d/SConstruct

https://www.ostricher.com/2014/09/scons-multi-module-with-build-dir/

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