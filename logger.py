# -*- coding: UTF-8 -*-
from __future__ import print_function
import logging
import os
import errno
import shutil
import os.path
from datetime import datetime
from six.moves import input
import sys

__all__ = ['set_logger_dir', 'disable_logger', 'auto_set_dir', 'set_logger_level']

def mkdir_p(dirname):
    """ Make a dir recursively, but do nothing if the dir exists
        Args:
            dirname(str): directory name
    """
    assert dirname is not None
    if dirname == '' or os.path.isdir(dirname):
        return
    try:
        os.makedirs(dirname)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise e

class _MyFormatter(logging.Formatter):
    def format(self, record):
        date = '[%(asctime)s @%(filename)s:%(lineno)d]'
        msg = '%(message)s'
        if record.levelno == logging.WARNING:
            fmt = 'WAR: ' + date + ' ' + msg
        elif record.levelno == logging.ERROR or record.levelno == logging.CRITICAL:
            fmt = 'ERR:  ' + date + ' ' + msg
        elif record.levelno == logging.DEBUG:
            fmt = 'DEBUG: ' + date + ' ' + msg
        else:
            fmt = 'INFO: ' + date + ' ' + msg
        if hasattr(self, '_style'):
            # Python3 compatibilty
            self._style._fmt = fmt
        self._fmt = fmt
        return super(_MyFormatter, self).format(record)


def _getlogger():
    logger = logging.getLogger('')
    logger.propagate = False
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_MyFormatter(datefmt='%m%d %H:%M:%S'))
    logger.addHandler(handler)
    return logger


_logger = _getlogger()
_LOGGING_METHOD = ['info', 'warning', 'error', 'critical', 'warn', 'exception', 'debug']
# export logger functions
for func in _LOGGING_METHOD:
    locals()[func] = getattr(_logger, func)


def get_time_str():
    return datetime.now().strftime('%m%d--%H-%M-%S')

LEVELS = ['DEBUG', 'INFO', 'WAR', 'ERR']

def set_logger_level(level):
    if level not in LEVELS:
        print('available levels: '.format(LEVELS))
        raise RuntimeError('Level is not supported!')
    if level == 'DEBUG':
        _logger.setLevel(logging.DEBUG)
    if level == 'INFO':
        _logger.setLevel(logging.INFO)
    elif level == 'WAR':
        _logger.setLevel(logging.WARN)
    else:
        _logger.setLevel(logging.ERROR)


# logger file and directory:
global LOG_FILE, LOG_DIR
LOG_DIR = None

def _set_file(path):
    if os.path.isfile(path):
        backup_name = path + '.' + get_time_str()
        shutil.move(path, backup_name)
        info("Log file '{}' backuped to '{}'".format(path, backup_name))  # noqa: F821
    hdl = logging.FileHandler(
        filename=path, encoding='utf-8', mode='w')
    hdl.setFormatter(_MyFormatter(datefmt='%m%d %H:%M:%S'))
    _logger.addHandler(hdl)
    _logger.info("Argv: " + ' '.join(sys.argv))

def set_logger_dir(dirname, log_file_name=None, verbose=True):
    """
    Set the directory and log filename for global logging.
    Args:
        dirname(str): log directory
        log_file_name(str): log filename
    """
    global LOG_FILE, LOG_DIR
    if not os.path.exists(dirname):
        mkdir_p(dirname)
    
    LOG_DIR = dirname
    if log_file_name is None:
        name = get_time_str() + '-log.log'
        if verbose: print('log file name is not set, use current-date-log.log as the default name')
    else:
        name = log_file_name
    LOG_FILE = os.path.join(dirname, name)
    if verbose: print('log file name is {}'.format(LOG_FILE))
    _set_file(LOG_FILE)


def disable_logger():
    """ Disable all logging ability from this moment"""
    for func in _LOGGING_METHOD:
        globals()[func] = lambda x: None


def auto_set_dir(verbose=True):
    """
    Set log directory to a subdir inside "train_log", with the name being
    the main python file currently running"""
    if LOG_DIR is not None:
        # dir already set
        return
    mod = sys.modules['__main__']
    basename = os.path.basename(mod.__file__)
    set_logger_dir(os.path.join('log', basename[:basename.rfind('.')]), verbose=verbose)


#if __name__ == '__main__':
#    set_logger_dir('./log')
#    _logger.info('invoked in main')
#    _logger.warning('warning')
#    _logger.error('error')