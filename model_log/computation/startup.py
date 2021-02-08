from .. import state, utils, template
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
    """
        There are three levels of config: local, project, global.
        Local takes precedent over project + gloabl, and project does over global.
    """

    tmpl = template.get_template()

    _config = {}

    def read_config(file_name):
        try:
            c = utils.read_yaml(file_name)
        except Exception as e:
            c = {}

        return c

    #try load global config
    global_config = read_config(tmpl['global_config'])
    _config = utils.add_dicts([_config, global_config])

    #try load project config
    project_config = read_config(tmpl['project_config'])
    _config = utils.add_dicts([_config, project_config])

    #try load local config
    local_config = read_config(tmpl['local_config'])
    _config = utils.add_dicts([_config, local_config])

    if state.verbose:
        logger.info('Experiment config: ')
        utils.print_dict(_config)


    return _config
