import os
from loguru import logger
import builtins
from types import ModuleType

from .. import template
from .. import utils
from .. import config

old_imp = builtins.__import__

class DummyModule(ModuleType):
    def __getattr__(self, key):
        return None
    __all__ = []   # support wildcard imports

def set_custom_import():
    """
        When import configs we may in another python enviroment (ie a specific plotting environment) but we still need to be able to load
            the configs the model dirs.

        To get around this we add an import hook to create dummy modules when laoding configs.

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



def get_experiment_name():
    """
        The experiment name is the same as the root folder that stores the experiment  
    """
    cwd = os.getcwd().split('/')

    tmpl = template.get_template()

    #This function is called in relation to the run file 
    #get the depth of the run file w.r.t to the base folder
    run_folder_depth = len(utils.split_path(tmpl['run_dir']))

    basename = cwd[-run_folder_depth]

    if tmpl['experiment_prefix'] is not None:
        experiment_prefix = tmpl['experiment_prefix']

        name = f"{experiment_prefix}_{basename}"
    else:
        name = f"{basename}"

    return name




def get_configs_from_model_files():
    """
        Assumes that all configs are defined within the model files:
            models/m_{name}.py

        and that each model file has a get_config() option which returns an array of all configs.
        Each config in the array must have the following keys:

            order_id: that acts as a unique ID within each config list
            experiment_id: that acts as a global ID across all experiments in models/

        If these are not provided they will be automatically generated. Optional fields

            fold_id: ID that is constant for all configs within a fold
    """

    tmpl = template.get_template()
    model_root = tmpl['model_dir']
    
    experiment_files = [filename for filename in os.listdir(model_root) if filename.startswith("m_")]

    if len(experiment_files) == 0:
        raise RuntimeError('No models found in {path}'.format(path=os.getcwd()+'/'+model_root))

    experiment_config_arr = []

    set_custom_import()

    for experiment in experiment_files:
        #logger does not exit on default

        if config.verbose:
            logger.info(f'Loading configs from {experiment}')

        @logger.catch
        def load():
            mod = utils.load_mod(model_root, experiment)
            
            #each model file must define an experiment variable called ex

            experiment_configs = mod.ex.config_function()

            for i, config in enumerate(experiment_configs):
                #config = ensure_correct_fields_for_model_file_config(experiment, config, i)
                experiment_config_arr.append(config)

        load()

    reset_import()


    return experiment_config_arr
