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

_SEML_CONFIG_PATH = "~/.config/seml/"
_SEML_CONFIG_FILE = "mongodb.config"


def get_abs_path(f):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(f)))


def check_if_self_config_exists():
    return os.path.exists(get_abs_path(_SEML_CONFIG_PATH + _SEML_CONFIG_FILE))


def create_default_selm_config():
    p = pathlib.Path(get_abs_path(_SEML_CONFIG_PATH + _SEML_CONFIG_FILE))
    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w") as f:
        f.write(_SEML_DEFAULT)


def install():
    """
    Checks if SELM has already been setup, otherwise creates a default SELM config file
    """
    if not (check_if_self_config_exists()):
        create_default_selm_config()

    if state.verbose:
        logger.info("sdem is all set up!")
