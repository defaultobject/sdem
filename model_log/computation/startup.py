from .. import state, utils, template
from . import manager

from pathlib import Path
from loguru import logger

def check():
    """
        Runs startup checks:
            - ensures model log has been run in correct folder

        Returns:
            True: if the check has passed and the program should continue
            False: if the check has failes and the progam should halt
    """
    if not(Path('models').is_dir()):
        logger.info('No models folder, not in correct folder')
        return False

    return True

def load_config():
    
    _config = manager.get_experiment_config()

    if state.verbose:
        logger.info('Experiment config: ')
        utils.print_dict(_config)


    return _config
