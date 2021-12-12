import os
from loguru import logger
import pathlib
import builtins
from types import ModuleType
import uuid
from pathlib import Path
from typing import List

from .. import template
from .. import utils
from .. import state
from .. import dispatch

from ..results.local import get_run_configs

old_imp = builtins.__import__


class DummyModule(ModuleType):
    def __getattr__(self, key):
        return None

    __all__ = []  # support wildcard imports


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


def get_experiment_config(default_config):
    """
    There are two levels of config: local and project.
        Local takes precedent over project.
    """

    _config = default_config

    def read_config(file_name):
        try:
            c = utils.read_yaml(file_name)
        except Exception as e:
            c = {}

        return c

    # try load project config
    project_config = read_config(
        _config["experiment_configs"]['project']
    )
    # update and overwrite _config
    _config = utils.add_dicts([_config, project_config])

    # try load local config
    local_config = read_config(
        _config["experiment_configs"]['local']
    )
    # update and overwrite _config
    _config = utils.add_dicts([_config, local_config])

    return _config


def get_experiment_folder_name():
    """
    The experiment name is the same as the root folder that stores the experiment
    """
    experiment_config = state.experiment_config

    cwd = os.getcwd().split("/")

    tmpl = template.get_template()

    # This function is called in relation to the run file
    # get the depth of the run file w.r.t to the base folder
    run_folder_depth = len(utils.split_path(tmpl["run_dir"]))

    basename = cwd[-run_folder_depth]

    return basename


def get_experiment_name():
    experiment_config = state.experiment_config

    basename = get_experiment_folder_name()

    if "experiment_name_prefix" in experiment_config.keys():
        experiment_prefix = experiment_config["experiment_name_prefix"]

        name = f"{experiment_prefix}_{basename}"
    else:
        name = f"{basename}"

    return name


def ensure_correct_fields_for_model_file_config(
    experiment: Path, config: dict, i: int
) -> dict:
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
    config["filename"] = experiment.name

    # add empty keys that can be used to add configs after experiment runs without affect IDs
    additional_key = "__tmp__{i}"

    for new_key_idx in range(10):
        new_key = additional_key.format(i=new_key_idx)
        if new_key not in config.keys():
            config[new_key] = None

    if "fold" in config.keys():
        # if the experiment has folds get a fold_id that is constistent across folds
        if "fold_group_id" not in config.keys():
            # get hash without fold key so that all fold_ids across folds will be consistent
            fold_group_id = utils.get_dict_hash(
                utils.get_dict_without_key(config, "fold")
            )

    if "experiment_id" not in config.keys():
        experiment_id = utils.get_dict_hash(config)

    # get order_id AFTER fold because we want the fold_id to be consistent across experiments, and the order_id is always incrememnting
    if "order_id" not in config.keys():
        config["order_id"] = i

    if "fold_group_id" not in config.keys():
        if "fold" not in config.keys():
            # if there is no folds set to be the same as experiment id
            fold_group_id = experiment_id
            config["fold"] = 0

        config["fold_group_id"] = fold_group_id

    if "experiment_id" not in config.keys():
        config["experiment_id"] = experiment_id

    if "global_id" not in config.keys():
        config["global_id"] = utils.get_unique_key()

    return config


def get_configs_from_model_files(experiment_config: dict, model_root=None) -> List[dict]:
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

    if model_root is None:
        model_root = Path(experiment_config['template']['folder_structure']['model_files'])
    else:
        model_root = Path(model_root)

    experiment_file_pattern = experiment_config['template']['experiment_file']

    # find all files in model_root that have the patten experiment_file_pattern
    matched_files = model_root.glob(experiment_file_pattern) 

    # only keep valid files
    experiment_files = [f for f in matched_files if f.is_file()]


    if len(experiment_files) == 0:
        raise RuntimeError(
            f"No models found in {model_root.resolve()} with pattern {experiment_file_pattern}"
        )

    # Go through every experiment file and store the found configs

    experiment_config_arr = []

    # enable the custom hook to avoid uncessary import errors
    set_custom_import()

    for experiment in experiment_files:

        if state.verbose:
            logger.info(f"Loading configs from {experiment}")

        # If an error occurs skip and continue
        #    logger does not exit when it catches an execption, just prints it
        @logger.catch
        def load():
            mod = utils.load_mod(experiment)

            # each model file must define an experiment variable called ex
            # use ex to get the configs
            experiment_configs = mod.ex.config_function()

            for i, config in enumerate(experiment_configs):
                config = ensure_correct_fields_for_model_file_config(
                    experiment, config, i
                )
                experiment_config_arr.append(config)

        #store here so we can revert
        cwd = os.getcwd()

        load()

        # revert back to orginal working directory
        os.chdir(cwd)


    # revert back to default import 
    reset_import()

    return experiment_config_arr


def get_valid_experiment_ids():
    configs = get_configs_from_model_files()
    return [c["experiment_id"] for c in configs]


def filter_configs(experiment_configs, filter_dict, run_new_only):
    """
    removes configs from experiment_configs that do not match filter_dict
    """
    if (type(filter_dict) == list and len(filter_dict) == 0) or (
        type(filter_dict) != list and len(filter_dict.keys()) == 0
    ):
        # nothing to filter
        _experiment_configs = experiment_configs
    else:
        if type(filter_dict) != list:
            filter_dict = [filter_dict]

        _experiment_configs = []
        for _filter in filter_dict:
            for config in experiment_configs:
                # check if config matches filter_dict
                if utils.dict_is_subset(_filter, config):
                    _experiment_configs.append(config)

    if run_new_only:
        # go through each config and check if a run exists for it

        # load all configs that have been run
        run_configs = get_run_configs(exp_root = './')

        # extract global ids
        run_experiment_ids = [config['experiment_id'] for config in run_configs]

        tmp = []

        for config in _experiment_configs:
            if config['experiment_id'] not in run_experiment_ids:
                tmp.append(config)

        _experiment_configs = tmp


    if state.verbose:
        logger.info(
            utils._s(
                "number of experiments before filter: ",
                len(experiment_configs),
                " and after ",
                len(_experiment_configs),
            )
        )

    return _experiment_configs


def create_default_experiment():
    tmpl = template.get_template()
    folders_to_create = [
        tmpl["model_dir"],
        tmpl["scared_run_files"],
        tmpl["results_files"],
        tmpl["data_files"],
    ]

    for _folder in folders_to_create:
        if _folder is not None:
            pathlib.Path(f"{_folder}").mkdir(parents=True, exist_ok=True)


def make_and_get_tmp_delete_folder(experiment_configs: dict) -> Path:
    """ Create a unique bin folder and returns the path. """
    bin_dir = experiment_configs['template']['folder_structure']['bin']

    # make bin directory
    bin_dir = Path(bin_dir)
    bin_dir.mkdir(exist_ok=True)

    # make unique id to store bin items
    _id = utils.get_unique_key()
    bin_id = bin_dir / _id 
    bin_id.mkdir()

    return bin_id


def remove_tmp_folder_if_empty(_id):
    tmpl = template.get_template()
    bin_dir = tmpl["bin_dir"]

    utils.delete_if_empty(f"{bin_dir}/{_id}")
    utils.delete_if_empty(f"{bin_dir}")

def construct_filter(_filter, filter_file):
    """
    Convert _filter to a dict. Load filter_file and then overwrite __filter.
    """
    filter_dict = utils.str_to_dict(_filter)

    _filter_from_file = {}
    if filter_file is not None:
        # filter from file will overwrite filter_dict
        # if a list of filters is defined in filter_file then filter_from_file will be a list of dictionaries
        _filter_from_file = utils.json_from_file(filter_file)

    if type(_filter_from_file) != list:
        _filter_from_file = [_filter_from_file]

    filter_from_file = []
    for _f in _filter_from_file:
        _f = utils.add_dicts([filter_dict.copy(), _f])
        filter_from_file.append(_f)

    return filter_from_file

def get_dispatched_fn(group: str, location: str, experiment_config: dict):
    """
    Find group function. We support two scenarios:
        1) the dispatch key is directly location. 
        2) the dispatch key is experiment_config[location]["type"]. 
     This allows a location to have its own function and also allows
        common code (ie for running on HPC cluster) to be used in multiple
        locations
    """

    fn = None

    if (location in experiment_config.keys()) and ('type' in experiment_config[location]):
        location_type = experiment_config[location]["type"]
        if dispatch.check(group, location_type):
            fn = dispatch.dispatch(group, location_type)

    if fn is None:
        if dispatch.check(group, location):
            fn = dispatch.dispatch(group, location)
        else:
            raise RuntimeError(f'No {group} function found for location {location}')

    return fn
