from .. import template
from .. import state
from ..utils import ask_permission
from ..computation import startup, manager

import os
from loguru import logger

def setup():
    #ensure we are not already in an experiment
    if startup.check():
        if state.verbose:
            logger.info('Folder already looks like an experiment. Cannot setup a new one!')

        return
    

    #ask permission to create new folders
    cwd = os.getcwd()
    ask_permission(
        f'Setup experiment here {cwd}?',
        manager.create_default_experiment
    )


