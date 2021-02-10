import os
from loguru import logger
import pathlib
import builtins
from types import ModuleType

from .. import template
from .. import utils
from .. import state

old_imp = builtins.__import__

class DummyModule(ModuleType):
    def __getattr__(self, key):
        return None
    __all__ = []   # support wildcard imports

def set_custom_import():
    """
        When importing configs we may be in another python enviroment (ie a specific plotting environment) but we still need to be able to load
            the configs define in the model files.

        To get around this we add an import hook to create dummy modules when loading the configs.

        If configs depend on a module that is not loaded then it should loudly fail.

    """

    def custom_import(name, *args, **kwargs):
        try:
            m = old_imp(name, *args, **kwargs)
        except Exception as e:
            m = DummyModule(name)

        return m

    builtins.__import__ = custom_import

def reset_import():
    builtins.__import__ = old_imp

def get_experiment_config():
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

    return _config

def get_experiment_folder_name():
    """
        The experiment name is the same as the root folder that stores the experiment  
    """
    experiment_config = state.experiment_config

    cwd = os.getcwd().split('/')

    tmpl = template.get_template()

    #This function is called in relation to the run file 
    #get the depth of the run file w.r.t to the base folder
    run_folder_depth = len(utils.split_path(tmpl['run_dir']))

    basename = cwd[-run_folder_depth]

    return basename



def get_experiment_name():
    experiment_config = state.experiment_config

    basename = get_experiment_folder_name()

    if 'experiment_name_prefix' in experiment_config.keys():
        experiment_prefix = experiment_config['experiment_name_prefix']

        name = f"{experiment_prefix}_{basename}"
    else:
        name = f"{basename}"

    return name

def ensure_correct_fields_for_model_file_config(experiment: str, config: dict, i: int) -> dict:
    """
        This method appends required items to config.
        items added:
            filename:  ensures that configs are unqiue across different files
            fold: if fold does not exist then is simply set to 0
            __tmp__{i}: 10 additional items are added. these can be used if an experiment wants to be changed without changing existing hashes.
            experiment_id: unique hash of each individual experiment run
            fold_group_id: uniqiue hash without fold  - so that experiments can be grouped across folds
            order_id: index of config in the full config array define in {filename}
            global_id: unqiue id across any run and file. is not included in experiment_id hash so that experiment_id's stay consistent.
        
    """
    config['filename'] = experiment

    #add empty keys that can be used to add configs after experiment runs without affect IDs
    additional_key = '__tmp__{i}'

    for new_key_idx in range(10):
        new_key = additional_key.format(i=new_key_idx)
        if new_key not in config.keys():
            config[new_key] = None

    if 'fold' in config.keys():
        #if the experiment has folds get a fold_id that is constistent across folds
        if 'fold_group_id' not in config.keys():
            #get hash without fold key so that all fold_ids across folds will be consistent
            fold_group_id = utils.get_dict_hash(utils.get_dict_without_key(config, 'fold'))

    if 'experiment_id' not in config.keys():
        experiment_id = utils.get_dict_hash(config)

    #get order_id AFTER fold because we want the fold_id to be consistent across, and the order_id is always incrememnting
    if 'order_id' not in config.keys():
        config['order_id'] = i

    if 'fold_group_id' not in config.keys():
        if 'fold' not in config.keys():
            #if there is no folds set to be the same as experiment id
            fold_group_id = experiment_id
            config['fold'] = 0

        config['fold_group_id'] = fold_group_id

    if 'experiment_id' not in config.keys():
        config['experiment_id'] = experiment_id

    if 'global_id' not in config.keys():
        config['global_id'] = utils.get_unique_key()

    return config


def get_configs_from_model_files():
    """
        Assumes that all configs are defined within the model files:
            models/m_{name}.py

        and that each model file has a get_config() option which returns an array of all configs.
        Each config in the array must have the following keys:

            order_id: that acts as a unique ID within each config list
            experiment_id: that acts as a global ID across all experiments in models/
            fold_group_id: ID that is constant for all configs within a fold

        If these are not provided they will be automatically generated. 
    """

    tmpl = template.get_template()
    model_root = tmpl['model_dir']
    
    experiment_files = [filename for filename in os.listdir(model_root) if filename.startswith("m_")]

    if len(experiment_files) == 0:
        raise RuntimeError('No models found in {path}'.format(path=os.getcwd()+'/'+model_root))

    experiment_config_arr = []

    set_custom_import()

    for experiment in experiment_files:

        if state.verbose:
            logger.info(f'Loading configs from {experiment}')

        #logger does not exit when it catches an execption, just prints it
        @logger.catch
        def load():
            mod = utils.load_mod(model_root, experiment)
            
            #each model file must define an experiment variable called ex
            experiment_configs = mod.ex.config_function()

            for i, config in enumerate(experiment_configs):
                config = ensure_correct_fields_for_model_file_config(experiment, config, i)
                experiment_config_arr.append(config)

        load()

    reset_import()

    return experiment_config_arr

def filter_configs(experiment_configs, filter_dict):
    """
        removes configs from experiment_configs that do not match filter_dict
    """
    if len(filter_dict.keys()) == 0:
        #nothing to filter
        _experiment_configs = experiment_configs
    else:

        _experiment_configs = []
        for config in experiment_configs:
            #check if config matches filter_dict
            if utils.dict_is_subset(filter_dict, config):
                _experiment_configs.append(config)

    if state.verbose:
        logger.info(utils._s('number of experiments before filter: ', len(experiment_configs), ' and after ', len(_experiment_configs)))

    return _experiment_configs

def create_default_experiment():
    tmpl = template.get_template()
    folders_to_create = [
        tmpl['model_dir'],
        tmpl['scared_run_files'],
        tmpl['results_files'],
        tmpl['data_files']
    ]

    for _folder in folders_to_create:
        if _folder is not None:
            pathlib.Path(f'{_folder}').mkdir(parents=True, exist_ok=True) 
