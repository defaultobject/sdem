import os
from loguru import logger
import pathlib
import builtins
from types import ModuleType
import uuid
from pathlib import Path
from typing import List
from string import Formatter

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


def get_experiment_config(state, default_config, exp_root = None):
    """
    There are three levels of config: default, project and local.
        Local takes precedent over project, and project over default.
    """

    with state.console.status("Finding root") as status:
        if exp_root is None:
            exp_root = Path('.')

        state.console.print(f'Root is {exp_root}')

        _config = default_config

        def read_config(file_name: Path):

            status.update(f'Loading config {file_name}')

            if file_name.exists():
                try:
                    c = utils.read_yaml(file_name)
                    state.console.log(f'Loaded {file_name}')
                except Exception as e:
                    # The yaml file must not be valid
                    logger.info(e)
                    c = {}
                    state.console.log(f'Error occured on {file_name} -- Skipping!')
            else:
                state.console.log(f'Config file {file_name} does not exist')
                c = {}

            return c

        # try load project config
        project_config = read_config(
            exp_root / _config["experiment_configs"]['project']
        )
        # update and overwrite _config
        _config = utils.add_dicts([_config, project_config])

        # try load local config
        local_config = read_config(
            exp_root / _config["experiment_configs"]['local']
        )
        # update and overwrite _config
        _config = utils.add_dicts([_config, local_config])

        return _config


def get_experiment_folder_name(experiment_config: dict) -> str:
    """
    The experiment name is the same as the root folder that stores the experiment
    """
    return Path.cwd().name

def get_experiment_name(experiment_config) -> str:
    basename = get_experiment_folder_name(experiment_config)

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


def get_model_files(state: 'State', model_root=None) -> List[Path]:
    experiment_config: dict = state.experiment_config

    if model_root is None:
        model_root = Path(experiment_config['template']['folder_structure']['model_files'])
    else:
        model_root = Path(model_root)

    experiment_file_pattern = experiment_config['template']['experiment_file']

    # find all files in model_root that have the patten experiment_file_pattern
    matched_files = model_root.glob(experiment_file_pattern) 

    # only keep valid files
    experiment_files = [f for f in matched_files if f.is_file()]

    return experiment_files

def get_configs_from_model_files(state: 'State', model_root = None, ignore_files: list = None) -> List[dict]:
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

    if ignore_files is None:
        ignore_files = []

    experiment_config: dict = state.experiment_config

    with state.console.status("Loading model configs") as status:

        experiment_files = get_model_files(state, model_root)


        if len(experiment_files) == 0:
            raise RuntimeError(
                f"No models found in {model_root.resolve()} with pattern {experiment_file_pattern}"
            )

        # Go through every experiment file and store the found configs

        experiment_config_arr = []

        # enable the custom hook to avoid uncessary import errors
        set_custom_import()

        for experiment in experiment_files:
            status.update(f"Loading configs from {experiment}")

            if experiment.name in ignore_files:
                # skip
                status.console.log(f'Ignoring {experiment}!')
                continue

            # If an error occurs skip and continue
            #    logger does not exit when it catches an execption, just prints it
            def load():
                try:
                    mod = utils.load_mod(experiment)

                    # each model file must define an experiment variable called ex
                    # use ex to get the configs
                    experiment_configs = mod.ex.config_function()

                    for i, config in enumerate(experiment_configs):
                        config = ensure_correct_fields_for_model_file_config(
                            experiment, config, i
                        )
                        experiment_config_arr.append(config)

                    status.console.log(f'Loaded configs from {experiment}')
                except Exception as e:
                    state.console.print(e)
                    status.console.log(f'!Error loading configs from {experiment} -- Skipping!')

            #store here so we can revert
            cwd = os.getcwd()

            load()

            # revert back to orginal working directory
            os.chdir(cwd)


        # revert back to default import 
        reset_import()

        return experiment_config_arr


def get_valid_experiment_ids(experiment_config):
    configs = get_configs_from_model_files(experiment_config)
    return [c["experiment_id"] for c in configs]


def filter_configs(state, experiment_configs, filter_dict, run_new_only):
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
        state.console.print(
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


def remove_tmp_folder(bin_path, experiment_config):
    tmp_path = get_tmp_folder_path(experiment_config)
    utils.move_dir_if_exists(tmp_path, bin_path)

def remove_bin_folder_if_empty(bin_path):
    utils.delete_if_empty(bin_path)
    utils.delete_if_empty(bin_path.parent)

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
    Group corresponds to the command that is being run (run, clean , sync, etc)
    
    There are multiple location types that we can act on (ie local, docker, cluster, etc)

    The location must have an entry in the experiment config and have a key 'type'

    For each group group function we support two scenarios:
        1) the dispatch key is directly location. 
        2) the dispatch key is experiment_config[location]["type"]. 

     This allows a location to have its own function and also allows
        common code (ie for running on HPC cluster) to be used in multiple locations
        and 2) takes precedence over 1) because then any dispatch_keys can be overwritten in the experiment_config 

    """

    fn = None

    # Check if type is defined in experiment_config
    if (location in experiment_config.keys()) and ('type' in experiment_config[location]):
        location_type = experiment_config[location]["type"]

        # if it is check if this can be used as the dispatch key
        if dispatch.check(group, location_type):
            fn = dispatch.dispatch(group, location_type)
    else:
        # Check if location should be used as the dispatch key
        if dispatch.check(group, location):
            fn = dispatch.dispatch(group, location)


    if fn is None:
        raise RuntimeError(f'No {group} function found for location {location}')

    return fn

def substitute_config_in_str(s: str, config: dict) -> str:
    """
    s is a string to be formatted. This function finds the required 
        keyword args and extracts them config and then formats s.
    """
    # get values to format
    formatter = Formatter().parse(s)

    field_names = [fname for _, fname, _, _ in formatter if fname]

    try:
        dict_to_pass = {
            k: config[k] for k in field_names
        }

        formatted_s = s.format(**dict_to_pass)
    except KeyError as e:
        logger.error(e)
        raise e


    return formatted_s
    
def get_sacred_runs_path(experiment_config, exp_root=None) -> Path:
    """ Return a Path object to the sacred runs/ folder """
    if exp_root is None:
        exp_root = Path('.')

    p = exp_root / Path(
        experiment_config['template']['folder_structure']['scared_run_files']
    )

    if not(p.exists()):
        logger.error(f'Folder {p} does not seem to exist - current working dir is {os.getcwd()}!')

    return p

def get_results_path(experiment_config, exp_root=None) -> Path:
    """ Return a Path object to the results folder """
    if exp_root is None:
        exp_root = Path('.')

    p = exp_root / Path(
        experiment_config['template']['folder_structure']['results']['root']
    )

    if not(p.exists()):
        logger.error(f'Folder {p} does not seem to exist - current working dir is {os.getcwd()}!')

    return p

def get_results_output_pattern(experiment_config) -> str:
    """ Return the expected results output format """
    return experiment_config['template']['folder_structure']['results']['file']

def get_tmp_folder_path(experiment_config, exp_root=None) -> Path:
    """ Return a Path object to the sdem temporary folder """
    if exp_root is None:
        exp_root = Path('.')

    p = exp_root / Path(
        experiment_config['template']['folder_structure']['tmp']
    )

    # temp is an optional folder so we do not check if it exists

    return p

def get_models_folder_path(experiment_config, exp_root=None) -> Path:
    """ Return a Path object to the models folder """
    if exp_root is None:
        exp_root = Path('.')

    p = exp_root / Path(
        experiment_config['template']['folder_structure']['model_files']
    )

    if not(p.exists()):
        logger.error(f'Folder {p} does not seem to exist - current working dir is {os.getcwd()}!')
    return p


