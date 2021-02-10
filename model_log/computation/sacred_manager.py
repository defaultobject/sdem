"""
    This file provides many of the wrappers around the sacred package.
"""
from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import numpy as np

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

from ..  import utils
from .. import template
from .. import state
from . import manager

from loguru import logger

def get_experiment_details():
    """
        Loads:
            experiment configs
            experiment_config yaml file
    """

    pass


def delete_id(folder_path, _id, tmp_folder_id):
    if state.verbose:
        logger.info(f'DELETING ID: {_id}')

    tmpl = template.get_template()
    bin_dir = tmpl['bin_dir']

    utils.move_dir_if_exists(folder_path, f"{bin_dir}/{tmp_folder_id}")


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
            logger.info('Error getting experiment start_time from experient run - ', _id)
            raise e

        sort_array.append([start_time])

    if len(sort_array) > 0:
        sort_args = np.argsort(sort_array, axis=0)[:, 0]
        return [experiment_folders[s] for s in sort_args]

    return []

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
            logger.info('Error getting experiment _id from experient run - ', _id)
            raise e

        experiment_ids.append(experiment_id)
    return experiment_ids



def prune_experiments(tmp_id):
    """
        Removes all local experiment folders that do not have a valid config id and removes all but the last of each config_id
    """
    experiment_config = state.experiment_config

    tmpl = template.get_template()
    runs_root = tmpl['scared_run_files']

    experiment_folders = [folder for folder in os.listdir(runs_root) if folder.isnumeric()]

    #experiment ids ordered by date
    experiment_folders =  order_experiment_folders_by_datetime(experiment_folders)
    all_experiment_ids = get_experiment_ids_from_folders(experiment_folders)

    valid_experiment_ids = manager.get_valid_experiment_ids()


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
            logger.info(f'Error getting experiment {_id} from experient run - deleting')
            delete_id(folder_path, _id, tmp_id)
            continue

        if experiment_id not in valid_experiment_ids:
            if state.verbose:
                logger.info(f'deleting {_id} because it is not a valid experiment id')

            delete_id(folder_path, _id, tmp_id)

        #+1 because we want to see if the experiment id was run AFTER this current run
        if experiment_id in all_experiment_ids[i+1:]:
            if state.verbose:
                logger.info(f'deleting {_id} because a newer run exists')

            delete_id(folder_path, _id, tmp_id)
