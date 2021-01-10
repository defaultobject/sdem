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


def get_experiment_details():
    """
        Loads:
            experiment configs
            experiment_config yaml file
    """

    pass

