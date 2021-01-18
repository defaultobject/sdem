import os
from pathlib import Path

from .util import load_mod, get_dict_hash, get_dict_without_key
from .  import settings

from . import sacred_storage_converter
from . import sacred_manager
from . import util

import json
import dateutil
import uuid

import numpy as np
import dateutil.parser

import builtins
from types import ModuleType

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


def ensure_correct_fields_for_model_file_config(experiment: str, config: dict, i: int) -> dict:
    config['filename'] = experiment

    #add empty keys that can be used to add configs after experiment runs without affect IDs
    additional_key = '__tmp__{i}'

    for new_key_idx in range(10):
        new_key = additional_key.format(i=new_key_idx)
        if new_key not in config.keys():
            config[new_key] = None

    if 'fold' in config.keys():
        #if the experiment has folds get a fold_id that is constistent across folds
        if 'fold_id' not in config.keys():
            #get hash without fold key so that all fold_ids across folds will be consistent
            fold_id = get_dict_hash(get_dict_without_key(config, 'fold'))

    if 'experiment_id' not in config.keys():
        experiment_id = get_dict_hash(config)

    #get order_id AFTER fold because we want the fold_id to be consistent across, and the order_id is always incrememnting
    if 'order_id' not in config.keys():
        config['order_id'] = i

    if 'fold_id' not in config.keys():
        if 'fold' not in config.keys():
            #if there is no folds set to be the same as experiment id
            fold_id = experiment_id
            config['fold'] = 0

        config['fold_id'] = fold_id

    if 'experiment_id' not in config.keys():
        config['experiment_id'] = experiment_id

    if 'global_id' not in config.keys():
        config['global_id'] = uuid.uuid4().hex

    return config

def get_configs_from_model_files(model_root = 'models/'):
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
    
    set_custom_import()

    experiment_files = [filename for filename in os.listdir(model_root) if filename.startswith("m_")]

    if len(experiment_files) == 0:
        raise RuntimeError('No models found in {path}'.format(path=os.getcwd()+'/'+model_root))

    experiment_config_arr = []
    for experiment in experiment_files:
        try:
            mod = load_mod(model_root, experiment)
            #experiment_configs = mod.get_config()
            experiment_configs = mod.ex.config_function()

            for i, config in enumerate(experiment_configs):
                config = ensure_correct_fields_for_model_file_config(experiment, config, i)
                experiment_config_arr.append(config)
        except Exception as e:
            if settings.verbose_flag:
                print('Could not load {f} -- ignoring!'.format(f=experiment))
                print(e)
                raise e


    reset_import()

    return experiment_config_arr

def dict_is_subset(dict1, dict2):
    """
        Return true if dict1 is a subset of dict2. 
            If dict1 has iterable items then this will be treated as an OR function.
    """
    #return all(item in dict2.items() for item in dict1.items())
    is_subset=True
    for k, i in dict1.items():
        if k not in dict2.keys():
            is_subset=False
            break

        if type(i) is list:
            #if is a list then either the element is a list or we need to sum over the list
            if type(dict2[k]) is list:
                #matching lists
                if dict2[k] == dict1[k]:
                    continue

            else:
                #loop through dict1 and check if any match
                any_matched = False
                for item in dict1[k]:
                    if dict2[k] == item:
                        any_matched = True
                        break
                if not any_matched:
                    is_subset=False
                    break
        else:
            if dict1[k] != dict2[k]:
                is_subset=False
                break



    return is_subset

def get_filtered_configs_from_model_files(filter_dict):
    experiment_configs = get_configs_from_model_files()

    if len(filter_dict.keys()) == 0:
        #nothing to filter
        return experiment_configs

    _experiment_configs = []
    for config in experiment_configs:
        #check if config matches filter_dict
        if dict_is_subset(filter_dict, config):
            _experiment_configs.append(config)

    if settings.verbose_flag:
        print('number of experiments before filter: ', len(experiment_configs), ' and after ', len(_experiment_configs))
    return _experiment_configs


def order_experiment_folders_by_datetime(experiment_folders):
    runs_root = 'models/runs'
    sort_array = []
    for _id in experiment_folders:
        folder_path = runs_root+'/'+_id
        try:
            with open('{root}/{_id}/run.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                start_time = dateutil.parser.parse(d['start_time'])
        except Exception as e:
            print('Error getting experiment start_time from experient run - ', _id)
            raise e

        sort_array.append([start_time])

    if len(sort_array) > 0:
        sort_args = np.argsort(sort_array, axis=0)[:, 0]
        return [experiment_folders[s] for s in sort_args]
    return []

def sync_filestorage_with_mongo(experiment_config, run_config):
    runs_root = 'models/runs'
    experiment_folders = [folder for folder in os.listdir(runs_root) if folder.isnumeric()]
    experiment_folders = order_experiment_folders_by_datetime(experiment_folders)
    #sort by datetime

    collection = experiment_config['collection']

    sacred_manager.remove_entries(collection)
    sacred_manager.cleanup(collection)

    for _id in experiment_folders:
        _id = int(_id)
        #get experiment+id
        try:
            with open('{root}/{_id}/config.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                experiment_id = d['experiment_id']
                fold_id = d['fold_id']
                global_id = d['global_id']
        except Exception as e:
            print('Error getting experiment _id from experient run - ', _id)
            raise e

        #check if _id exists in mongo db
        insert_id = None
        for row in collection.find({'config.experiment_id': experiment_id}):
            insert_id = row['_id']
            break #should only be one config with experiment_id

        try:
            sacred_storage_converter.file_storage_to_mongo_db(experiment_config['experiment_name'], collection, 'models/runs', _id, insert_id, overwrite=True)
        except:
            # If there is an error then it suggests that the experiment was not able to finish, so instead try adding an error entry to the DB
            if settings.verbose_flag:
                print('There was a problem with experiment: ', experiment_config['experiment_name'], ', inserting error entry')
            sacred_storage_converter.file_storage_to_mongo_db(experiment_config['experiment_name'], collection, 'models/runs', _id, insert_id, overwrite=True, error_entry=True)


def get_valid_experiment_ids():
    configs = get_configs_from_model_files()
    return [c['experiment_id'] for c in configs]

def make_and_get_tmp_delete_folder():
    _id = uuid.uuid4().hex
    Path("models/tmp").mkdir(exist_ok=True)
    Path(f"models/tmp/{_id}").mkdir(exist_ok=True)
    return _id

def remove_tmp_folder_if_empty(_id):
    util.delete_if_empty(f"models/tmp/{_id}")
    util.delete_if_empty("models/tmp")


def delete_id(folder_path, _id, tmp_folder_id):
    if settings.verbose_flag:
        print('DELETING ID: ', _id)

    util.move_dir_if_exists(folder_path, f"models/tmp/{tmp_folder_id}")

def get_experiment_ids_from_folders(experiment_folders):
    runs_root = 'models/runs'
    experiment_ids = []
    for _id in experiment_folders:
        folder_path = runs_root+'/'+_id

        _id = int(_id)
        #get experiment+id
        try:
            with open('{root}/{_id}/config.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                experiment_id = d['experiment_id']
        except Exception as e:
            print('Error getting experiment _id from experient run - ', _id)
            raise e

        experiment_ids.append(experiment_id)
    return experiment_ids


def prune_experiments(experiment_config, run_config, tmp_id):
    """
        Removes all local experiment folders that do not have a valid config id and removes all but the last of each config_id
    """
    runs_root = 'models/runs'
    experiment_folders = [folder for folder in os.listdir(runs_root) if folder.isnumeric()]
    #experiment ids ordered by date
    experiment_folders =  order_experiment_folders_by_datetime(experiment_folders)
    all_experiment_ids = get_experiment_ids_from_folders(experiment_folders)

    valid_experiment_ids = get_valid_experiment_ids()


    collection = experiment_config['collection']
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root+'/'+_id

        _id = int(_id)
        #get experiment+id
        try:
            with open('{root}/{_id}/config.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                global_id = d['global_id']
                experiment_id = d['experiment_id']
        except Exception as e:
            print('Error getting experiment _id from experient run - ', _id)
            raise e

        if experiment_id not in valid_experiment_ids:
            delete_id(folder_path, _id, tmp_id)

        #+1 because we want to see if the experiment id was run AFTER this current run
        if experiment_id in all_experiment_ids[i+1:]:
            delete_id(folder_path, _id, tmp_id)

def delete_empty_experiments(runs_root, experiment_folders, tmp_id):

    _experiment_folders = [] 
    for folder in experiment_folders:
        if not os.listdir(runs_root+'/'+folder):
            delete_id(runs_root+'/'+folder, folder, tmp_id)
        else:
            _experiment_folders.append(folder)

    return _experiment_folders


def prune_unfinished(experiment_config, run_config):
    runs_root = 'models/runs'
    experiment_folders = [folder for folder in os.listdir(runs_root) if folder.isnumeric()]

    tmp_id = make_and_get_tmp_delete_folder()

    #check that experiment_folders are not empty

    experiment_folders = delete_empty_experiments(runs_root, experiment_folders, tmp_id)

    #experiment_folders = order_experiment_folders_by_datetime(experiment_folders)

    all_experiment_ids = get_experiment_ids_from_folders(experiment_folders)
    #sort by datetime


    collection = experiment_config['collection']
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root+'/'+_id

        _id = int(_id)
        #get experiment+id
        try:
            with open('{root}/{_id}/config.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                experiment_id = d['experiment_id']
                fold_id = d['fold_id']
                global_id = d['global_id']

            with open('{root}/{_id}/run.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                status = d['status']
        except Exception as e:
            print('Error getting experiment _id from experient run - ', _id)
            delete_id(folder_path, _id, tmp_id)
            raise e

        if status != 'COMPLETED': 
            delete_id(folder_path, _id, tmp_id)
        else:
            print('KEEPING: ', _id)




def order_experiment_folders(experiment_folders):
    runs_root = 'models/runs'
    sort_array = []
    for _id in experiment_folders:
        folder_path = runs_root+'/'+_id
        try:
            with open('{root}/{_id}/config.json'.format(root=runs_root, _id=_id)) as f:
                d = json.load(f)
                filename = d['filename']
                order_id = d['order_id']
        except Exception as e:
            print('Error getting experiment _id from experient run - ', _id)
            raise e

        sort_array.append([filename, order_id])

    if len(sort_array) > 0:
        sort_args = np.argsort(sort_array, axis=0)[:, 0]
        return [experiment_folders[s] for s in sort_args]

    return []


def fix_filestorage_ids(experiment_config, run_config):
    """
        Goes through the data twice, once to rename to a temp name to avoid conflict and then to rename to the correct format
    """
    runs_root = 'models/runs'
    
    experiment_folders = [folder for folder in os.listdir(runs_root) if folder.isnumeric()]
    #sort experiments by filename and order_id so that the _ids are consistent 
    experiment_folders = order_experiment_folders(experiment_folders)

    collection = experiment_config['collection']
    to_change = []
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root+'/'+_id

        _id = int(_id)
        new_id = i+1

        new_folder_path = runs_root+'/'+str(new_id)+'.tmp'

        to_change.append(new_folder_path)

        if settings.verbose_flag:
            print('Renaming: ', folder_path, ' to ', new_folder_path)
        os.rename(folder_path, new_folder_path)

    for _file in to_change:
        new_folder_path = os.path.splitext(_file)[0]

        if settings.verbose_flag:
            print('Renaming: ', _file, ' to ', new_folder_path)
        os.rename(_file, new_folder_path)

def prune_and_fix_experiment_ids(experiment_config, run_config, _id):
    prune_experiments(experiment_config, run_config, _id)
    fix_filestorage_ids(experiment_config, run_config)

