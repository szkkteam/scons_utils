import os
import sys
from   SCons.Script import *
import json

from logger import _logger


COMPILER_DEFINITION_FILE="compilers.json"

def loadCompilerDefinition(fileName):
    fullPath = Path(fileName)
    if fullPath.suffix != ".json":
    	_logger.error("File type: %s is not a JSON file" % (fullPath.suffix))
        sys.exit(100)
    try:
        with open(str(fullPath), "r") as read_file:
            dataStream = json.load(read_file)
    except FileNotFoundError as fnf_error:
        _logger.error(
            "Configuration file \'%s\' is not exists." % (fullPath.name))
        sys.exit(101)
    except json.JSONDecodeError as json_err:
        _logger.error(
            "Configuration file \'%s\' is damaged. Error: %s." % (fullPath.name, json_err))
        sys.exit(102)

    return dataStream

