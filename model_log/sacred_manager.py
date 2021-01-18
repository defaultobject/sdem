from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import os
import seml.queuing

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess

import hashlib

import copy

from .util import print_dict

def get_experiment_name():
    return os.getcwd().split('/')[-1]

def get_db():
    try :
        mongodb_config = seml.database.get_mongodb_config()
        db = seml.database.get_database(**mongodb_config)
        return db
    except Exception as e:
        print('Check that mongodb is running?')
        print(e)
        raise e

def get_collection(name):
    collection = seml.database.get_collection(name)
    return collection

def get_experiments_collection():
    db = get_db()
    collections = db.collection_names()

    project_dir = os.path.dirname(os.getcwd())
    experiment_name = get_experiment_name()

    collection_name = experiment_name+'_runs'
    collection = seml.database.get_collection(collection_name)

    return collection

def clean_unreferenced_sources(collection):
    mongodb_config = seml.database.get_mongodb_config()
    db = seml.database.get_database(**mongodb_config)

    fs = gridfs.GridFS(db)

    for f in collection.find():
        referenced_ids = []
        if 'experiments' in f.keys() and 'sources' in f['experiments'].keys():
            referenced_ids = [a.source_id for a in f['experiments']['sources']]

    for f in fs.find():
        if f._id not in referenced_ids:
            fs.delete(f._id)

def remove_entries(collection):
    collection.remove({})

def cleanup(collection):

    #remove all artifacts
    try:
        seml.database.clean_unreferenced_artifacts(basedir)
        clean_unreferenced_sources(collection)
    except:
        pass


def get_sacred_ids_of_config_filter(collection,config_filter: dict=None, drop_global_id:bool=False):
    """
        Returns array of ids of experiment runs that match the given filters
        global_id is a globally unique id and so will stop the filters matching. setting drop_global_id will remove global id from the config filter
    """
    filter_dict = {}
    if config_filter is not  None:
        for k, i in config_filter.items():
            filter_dict['config.{k}'.format(k=k)] =  i

    if drop_global_id:
        if 'config.global_id' in filter_dict.keys():
            del  filter_dict['config.global_id']

        if 'config.experiment_id' in filter_dict.keys():
            del  filter_dict['config.experiment_id']

        if 'config.order_id' in filter_dict.keys():
            del  filter_dict['config.order_id']

    cursor = collection.find(filter_dict)

    _ids = []
    for x in cursor:
        _ids.append(x['_id'])

    return _ids

def get_sacred_ids_of_configs(collection, configs, drop_global_id:bool=False):
    _id_arr = []
    for config in configs:
        config = copy.deepcopy(config)
        _ids = get_sacred_ids_of_config_filter(collection, config, drop_global_id)
        _id_arr.append(_ids)
    return _id_arr

def get_sacred_attributes_of_experiement_filter(collection, attr: str, filter_dict: dict):
    cursor = collection.find(filter_dict)

    attributes = []
    for x in cursor:
        attributes.append(x[attr])

    return attributes

def get_sacred_columns_of_experiement_filter(collection_name, filter_dict: dict):
    collection = get_collection(collection_name)
    cursor = collection.find(filter_dict)

    return list(cursor)


def get_fold_ids_that_match_config(experiment_name, filter_dicts):
    collection = get_collection(experiment_name)

    match_dict = {}

    for name, filter_dict in filter_dicts.items():
        
        rows = get_sacred_attributes_of_experiement_filter(
            collection, 
            'config',
            filter_dict
        )
        if len(rows) == 0:
            #raise RuntimeError('Could not find {n}'.format(n=name))
            print('get_fold_ids_that_match_config: Could not find {n}. Continuing!'.format(n=name))
            continue

        unique_ids = set([row['fold_id'] for row in rows])
        
        match_dict[name] = unique_ids
        
    return match_dict

def match_config_filters_to_fold_ids(experiment_name, filter_dicts):
    collection = get_collection(experiment_name)

    match_dict = {}
    
    for name, filter_dict in filter_dicts.items():
        
        rows = get_sacred_attributes_of_experiement_filter(
            collection, 
            'config',
            filter_dict
        )
        if len(rows) == 0:
            #raise RuntimeError('Could not find {n}'.format(n=name))
            print('match_config_filters_to_fold_ids: Could not find {n}. Continuing!'.format(n=name))
            continue

        unique_ids = set([row['fold_id'] for row in rows])
        
        if len(unique_ids) > 1:
            print('non-unique filter dict: ', filter_dict)
            print('matching ids: ', unique_ids)
            raise RuntimeError('There should only be one _id. Make sure that config filter is unique.')

        #match_dict[rows[0]['fold_id']] = name
        match_dict[name] = rows[0]['fold_id']
        
    return match_dict

def match_config_filters_to_experiment_ids(experiment_name, filter_dicts):
    collection = get_collection(experiment_name)

    match_dict = {}
    
    for name, filter_dict in filter_dicts.items():
        
        rows = get_sacred_attributes_of_experiement_filter(
            collection, 
            'config',
            filter_dict
        )
        if len(rows) == 0:
            #raise RuntimeError('Could not find {n}'.format(n=name))
            print('match_config_filters_to_experiment_ids: Could not find {n}. Continuing!'.format(n=name))
            continue

        unique_ids = set([row['experiment_id'] for row in rows])
        
        if len(unique_ids) > 1:
            print('non-unique filter dict: ')
            print_dict(filter_dict)
            print('matching ids: ', unique_ids)
            raise RuntimeError('There should only be one _id. Make sure that config filter is unique.')

        match_dict[name] = rows[0]['experiment_id']

    return match_dict


def get_sacred_ids_of_experiement_filter(collection, filter_dict: dict):
    return get_sacred_attributes_of_experiement_filter(collection, '_id', filter_dict)
    
def get_minimal_entry(_id: int, config: dict, status: str, name: str, start_time: datetime = None):
    current_time = datetime.datetime.now()

    exp_dict = {}
    exp_dict['_id'] = _id
    exp_dict['config'] = config
    exp_dict['status'] = status

    exp_dict['meta'] = {}
    exp_dict['host'] = {}

    exp_dict['heartbeat'] = current_time
    exp_dict['start_time'] = start_time
    
    exp_dict['experiment'] = {} 
    exp_dict['experiment']['name'] = name

    exp_dict['artifacts'] = []

    if start_time is not None:
        exp_dict['start_time']= start_time

    return exp_dict



def queue_runs(basedir, collection, configs):
    """
        Creates an empty experiment entry in the DB for every config. If config has already been entered in the DB then it will be overwritten.
    """
    for c in configs:
        if False:
            found_id = get_sacred_ids_of_config_filter(collection, config_filter=c)
        else:
            config_filter = {'config': {'experiment_id': c['experiment_id']}}
            found_id = get_sacred_ids_of_config_filter(collection, config_filter=c)

        if len(found_id) > 1:
            raise RunTimeError('Should only be on experiment with this config: ', c)

        max_id = seml.database.get_max_in_collection(collection, '_id')

        if max_id is None:
            max_id = 1
        else:
            max_id = max_id + 1

        if len(found_id) == 0:
            _id = max_id
        elif len(found_id) == 1:
            _id = found_id[0]

        #need to create new entry
        name = c['filename']
        start_time = datetime.datetime.utcnow()
        exp_dict = get_minimal_entry(_id, c, "QUEUED", name, start_time)

        collection.replace_one({'_id': _id}, exp_dict, upsert=True)

def get_ids_to_run(basedir, collection):
    """
        Assumes that all experiments have been entered into the MongoDB database and are either
            in COMPLETED or a queueing or failed state.
    """
    all_ids = get_sacred_ids_of_experiement_filter(collection, {})
    completed_ids = get_sacred_ids_of_experiement_filter(collection, {'status': 'COMPLETED'})

    ids_to_run = list(set(all_ids)- set(completed_ids))
    return ids_to_run

def get_exp_attributes_from_ids(collection, ids):
    configs_to_run = []
    for _id in ids:
        config_i = get_sacred_attributes_of_experiement_filter(collection, 'config', {'_id': _id})
        if len(config_i) == 0 or len(config_i) > 1:
            raise RunTimeError()

        config_i = config_i[0]
        configs_to_run.append(config_i['order_id'])
    return configs_to_run


