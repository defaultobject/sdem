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
from pathlib import Path

import numpy as np

import os

import slurmjobs
import slurmjobs.util as uti

import shutil
import zipfile
import subprocess

import hashlib

import copy

from .. import utils
from .. import template
from . import manager

from loguru import logger


def delete_id(folder_path: Path, bin_path: Path):
    _id = folder_path.name

    logger.info(f"DELETING ID: {_id} -> {bin_path}")

    utils.move_dir_if_exists(folder_path, bin_path)


def delete_result(f, bin_path: Path):
    name = f.name

    logger.info(f"DELETING Result: {name}")

    utils.move_dir_if_exists(f, bin_path)


def order_experiment_folders_by_datetime(runs_root: Path, experiment_folders:list) -> list:
    """ Return experiments from run_roots ordered by experiment start_time. """

    # Get experiments from run_roots
    sort_array = []
    for _id in experiment_folders:
        folder_path = runs_root / _id

        try:
            with open(folder_path / "run.json") as f:
                d = json.load(f)
                start_time = dateutil.parser.parse(d["start_time"])
        except Exception as e:
            logger.info(
                "Error getting experiment start_time from experient run - {_id}"
            )
            raise e

        sort_array.append([start_time])

    # Sort experiments by start time
    if len(sort_array) > 0:
        sort_args = np.argsort(sort_array, axis=0)[:, 0]
        return [experiment_folders[s] for s in sort_args]

    # Return empty list if nothing to sort
    return []


def get_experiment_ids_from_folders(runs_root: Path, experiment_folders: list) -> list:
    """ For each sacred experiment get the corresponding (unique) sdem experiment_id from the config file. """
    experiment_ids = []
    for _id in experiment_folders:
        folder_path = runs_root / _id

        _id = int(_id)

        # get experiment+id
        try:
            with open(folder_path / "config.json") as f:
                d = json.load(f)
                experiment_id = d["experiment_id"]
        except Exception as e:
            logger.info(f"Error getting experiment _id from experient run - {_id}")
            raise e

        experiment_ids.append(experiment_id)
    return experiment_ids


def delete_empty_experiments(runs_root: Path, experiment_folders: list, bin_path: Path) -> list:
    """
    Delete empty experiments from experiment_folders and remove from the list
    """
    _experiment_folders = []
    for folder in experiment_folders:
        if not os.listdir(runs_root / folder):
            delete_id(runs_root / folder, bin_path)
        else:
            _experiment_folders.append(folder)

    return _experiment_folders


def prune_unfinished(state, bin_path: Path, experiment_config: dict):
    """
    Go through every experiment and move to bin_path if:
        - the experiment folder is empty 
        - the status of the sacred experiment is not Completed
    """
    # Get sacred run root
    runs_root = manager.get_sacred_runs_path(experiment_config)

    # Load all sacred runs
    experiment_folders = get_sacred_experiment_folders(runs_root) 

    # Delete empty experiment folders
    experiment_folders = delete_empty_experiments(runs_root, experiment_folders, bin_path)
    all_experiment_ids = get_experiment_ids_from_folders(runs_root, experiment_folders)

    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root / _id

        _id = int(_id)
        try:
            with open(folder_path / "config.json") as f:
                d = json.load(f)
                experiment_id = d["experiment_id"]
                global_id = d["global_id"]

            with open(folder_path / "run.json") as f:
                d = json.load(f)
                status = d["status"]
        except Exception as e:
            if state.verbose:
                logger.info(f"Error getting experiment _id from experient run - {_id}")

            delete_id(folder_path, bin_path)
            continue

        if status != "COMPLETED":
            delete_id(folder_path, bin_path)

def get_sacred_experiment_folders(runs_root: Path) -> list:
    return [folder for folder in os.listdir(runs_root) if folder.isnumeric()]

def delete_all_experiments(state, bin_path: Path, experiment_config:dict):
    """ Removes all local experiment folders """
    # Load all sacred runs
    runs_root = manager.get_sacred_runs_path(experiment_config)
    experiment_folders = get_sacred_experiment_folders(runs_root) 

    experiment_folders = order_experiment_folders_by_datetime(runs_root, experiment_folders)
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root / _id
        _id = int(_id)

        delete_id(folder_path, bin_path)


def prune_experiments(state, bin_path: Path, experiment_config:dict):
    """
    Removes all local experiment folders that do not have a valid config id and removes all but the last of each config_id

    If multiple experiments run have the SAME start_time with the same experiment_id then it is not guarrenteed which one will be deleted and which will be saved. 
    """

    # First remove all experiments that have not finished running 
    #   i.e they are empty or their status !- COMPLETED
    prune_unfinished(state, bin_path, experiment_config)

    # Load all sacred runs
    runs_root = manager.get_sacred_runs_path(experiment_config)
    experiment_folders = get_sacred_experiment_folders(runs_root) 

    # experiment ids ordered by date
    experiment_folders = order_experiment_folders_by_datetime(runs_root, experiment_folders)
    all_experiment_ids = get_experiment_ids_from_folders(runs_root, experiment_folders)

    # Get all experiments_ids from configs
    valid_experiment_ids = manager.get_valid_experiment_ids(state)

    # Remove experiments that do not have a valid id and have been run multiple times, 
    #   saving only the most recent one
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root / _id
        _id = int(_id)

        try:
            with open(folder_path / "config.json") as f:
                d = json.load(f)
                global_id = d["global_id"]
                experiment_id = d["experiment_id"]
        except Exception as e:
            logger.info(f"Error getting experiment {_id} from experient run - deleting")
            delete_id(folder_path, bin_path)
            continue

        if experiment_id not in valid_experiment_ids:
            if state.verbose:
                logger.info(f"deleting {_id} because it is not a valid experiment id")

            delete_id(folder_path, bin_path)

        # Check if experiment_id exists multiply times
        # Since all_experiment_ids is ordred by start_time we only need to check if it exists
        #   in all_experiment_ids AFTER this one
        if experiment_id in all_experiment_ids[i + 1 :]:
            if state.verbose:
                logger.info(f"deleting {_id} because a newer run exists")

            delete_id(folder_path, bin_path)


def prune_results(state, bin_path: Path, experiment_config: dict):
    """
    Collects all configs
    Creates all valid results file
    Removes any result files that are not in this list

    """
    results_root = manager.get_results_path(experiment_config)
    all_configs = manager.get_configs_from_model_files(state)

    result_output_pattern = manager.get_results_output_pattern(experiment_config)


    valid_result_files = [
        manager.substitute_config_in_str(result_output_pattern, config)
        for config in all_configs
    ]

    results_folders = [f for f in os.listdir(results_root)]

    for res in results_folders:
        if res not in valid_result_files:
            delete_result(results_root / res, bin_path)


def fix_filestorage_ids(state, experiment_config):
    """
    Goes through the data twice, once to rename to a temp name to avoid conflict and then to rename to the correct format
    """

    runs_root = manager.get_sacred_runs_path(experiment_config)
    experiment_folders = get_sacred_experiment_folders(runs_root) 

    # sort experiments by datetime
    experiment_folders = order_experiment_folders_by_datetime(runs_root, experiment_folders)

    to_change = []
    for i, _id in enumerate(experiment_folders):
        folder_path = runs_root / _id
        _id = int(_id)

        # sacred run ids start from 1
        new_id = i + 1

        new_folder_path = runs_root /  f"{str(new_id)}.tmp"

        # Do not rename if it will overwrite something
        if new_folder_path.exists():
            logger.info(f'{new_folder_path} exists -- skipping!')
            continue

        to_change.append(new_folder_path)

        if state.verbose:
            logger.info(f"Renaming: {folder_path} -> {new_folder_path}")


        os.rename(str(folder_path), str(new_folder_path))

    for _file in to_change:
        new_folder_path = runs_root / _file.stem 

        # Do not rename if it will overwrite something
        if new_folder_path.exists():
            logger.info(f'{new_folder_path} exists -- skipping!')
            continue

        if state.verbose:
            logger.info(f"Renaming: {_file} -> {new_folder_path}")

        os.rename(str(_file), str(new_folder_path))
