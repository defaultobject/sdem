from .. import template
from .. import state
from ..utils import ask_permission
from ..computation import startup, manager

import pathlib

import os
from loguru import logger

_SEML_DEFAULT = """
username: default
password: default
port: 27017
database: sacred
host: localhost
"""

_SEML_CONFIG_PATH = '~/.config/seml/'
_SEML_CONFIG_FILE = 'mongodb.config'

def check_if_self_config_exists():
    return os.path.exists(_SEML_CONFIG_PATH+_SEML_CONFIG_FILE)

def create_default_selm_config():
    p = pathlib.Path(_SEML_CONFIG_PATH)
    p.mkdir(parents=True, exist_ok=True)

    (p / _SEML_CONFIG_FILE).write_text(_SEML_DEFAULT, encoding="utf-8")

def install():
    """
        Checks if SELM has already been setup, otherwise creates a default SELM config file
    """
    if not(check_if_self_config_exists()):
        create_default_selm_config()

    if state.verbose:
        logger.info('sdem is all set up!')

