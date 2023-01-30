from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import numpy as np

import os

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as uti

import shutil
import zipfile
import subprocess

import hashlib

import copy

from .. import utils
from .. import template
from .. import state
from . import manager, storage_converter, sacred_manager

from loguru import logger


def get_db():
    try:
        mongodb_config = seml.database.get_mongodb_config()
        db = seml.database.get_database(**mongodb_config)
        return db
    except Exception as e:
        logger.info("Check that mongodb is running?")
        print(e)
        raise e


def get_collection(name):
    """
    Return mongo collections
    """
    collection = seml.database.get_collection(name)
    return collection


def get_experiment_collection():
    db = get_db()
    collections = db.collection_names()

    experiment_name = manager.get_experiment_name()

    collection_name = experiment_name + "_runs"
    collection = seml.database.get_collection(collection_name)

    return collection


def clean_unreferenced_sources(collection):
    mongodb_config = seml.database.get_mongodb_config()
    db = seml.database.get_database(**mongodb_config)

    fs = gridfs.GridFS(db)

    for f in collection.find():
        referenced_ids = []
        if "experiments" in f.keys() and "sources" in f["experiments"].keys():
            referenced_ids = [a.source_id for a in f["experiments"]["sources"]]

    for f in fs.find():
        if f._id not in referenced_ids:
            fs.delete(f._id)


def remove_entries(collection):
    collection.remove({})


def cleanup_db(experiment_name, collection):
    seml.database.clean_unreferenced_artifacts(experiment_name)
    clean_unreferenced_sources(collection)


def sync():
    """
    Go through every model run
    Convert from local storage observer to a mongo observer
    Insert mongo observer into mongo db

    Notes:

    Before syncing we delete everything from the mongodb table, this not the most efficient but means we do not need to track what only needs to be synced. If this is too slow perhaps consider only using local observers.

    We sort the model runs before inserting because they will be overwritten in the DB. the DB should only hold the most recent runs.
    """

    tmpl = template.get_template()
    runs_root = tmpl["scared_run_files"]

    experiment_folders = [
        folder for folder in os.listdir(runs_root) if folder.isnumeric()
    ]
    experiment_folders = sacred_manager.order_experiment_folders_by_datetime(
        experiment_folders
    )

    collection = get_experiment_collection()
    experiment_name = manager.get_experiment_name()

    # delete_collection(collection)
    cleanup_db(experiment_name, collection)

    for _id in experiment_folders:
        _id = int(_id)
        # get experiment+id

        # if an experiment finishes before - ie memory errors etc, experiment_id will not exist
        try:
            with open(f"{runs_root}/{_id}/config.json") as f:
                d = json.load(f)
                experiment_id = d["experiment_id"]
                fold_id = d["fold_id"]
                global_id = d["global_id"]
        except Exception as e:
            if state.verbose:
                logger.info(
                    f"Error getting experiment _id from experient run {_id} - ignoring!"
                )
            # raise e

        # check if _id exists in mongo db so that we can overwrite if required
        insert_id = None
        for row in collection.find({"config.experiment_id": experiment_id}):
            insert_id = row["_id"]
            break  # should only be one config with experiment_id

        try:
            storage_converter.file_storage_to_mongo_db(
                experiment_name,
                collection,
                "models/runs",
                _id,
                insert_id,
                overwrite=True,
            )
        except:
            # If there is an error then it suggests that the experiment was not able to finish, so instead try adding an error entry to the DB
            if state.verbose:
                logger.info(
                    f"There was a problem with experiment {experiment_name} inserting error entry {_id}"
                )

            storage_converter.file_storage_to_mongo_db(
                experiment_name,
                collection,
                "models/runs",
                _id,
                insert_id,
                overwrite=True,
                error_entry=True,
            )
