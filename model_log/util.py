from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import os
import sys

import importlib
import importlib.util
import seml.queuing

import yaml

import shutil
import zipfile
import subprocess

import itertools 

import hashlib

import typing

from pathlib import Path

import copy

def print_dict(_dict):
    print(json.dumps(_dict, indent=3))

def get_dict_without_key(_dict, key):
    return {i:_dict[i] for i in _dict if i != key}

def get_dict_hash(_dict):
    """
        Args:
            _dict (dict) - a single configuration
        Returns:
            md5 hash of the sorted _dict
    """
    return hashlib.md5(json.dumps(_dict, sort_keys=True).encode('utf-8')).hexdigest()

def load_mod(root, file_name):
    cwd = os.getcwd()
    #cd into root so that relative paths inside file_name still work
    os.chdir(root)
    spec = importlib.util.spec_from_file_location("", file_name)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    #revert back to orginal working directory
    os.chdir(cwd)
    return foo

def add_dicts(dict_array: typing.List[dict], deepcopy=False) -> dict:
    """
        Adds all dicts in dict_array into the first dict and returns this.
    """
    sum_dict = None
    for d in dict_array:
        if copy:
            d = copy.deepcopy(d)

        if sum_dict is None:
            sum_dict = d
        else:
            sum_dict.update(d)

    return sum_dict


def mkdir_if_not_exists(root):
    Path(root).mkdir(exist_ok=True)



def remove_dir_if_exists(root):
    if os.path.exists(root):
        shutil.rmtree(root)

def move_dir_if_exists(root, tmp_dir):
    if os.path.exists(root):
        shutil.move(root, tmp_dir)

def delete_if_empty(d):
    if len(os.listdir(d)) == 0:
        remove_dir_if_exists(d)

def get_digest_from_bytes(f):
    """Compute the MD5 hash for a given file."""
    h = hashlib.md5()
    data = f.read(1 * MB)
    while data:
        h.update(data)
        data = f.read(1 * MB)
    return h.hexdigest()

def zip_dir(path, zipf):
    for root, dirs, files in os.walk(path):
        for f in files:
            zipf.write(os.path.join(root, f))    

def read_yaml(file_name):
    #load experiment config
    with open(file_name) as f:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        ec = yaml.load(f, Loader=yaml.FullLoader)

    return ec

def get_all_permutations(options):
    #get all permutations of options
    keys, values = zip(*options.items())
    permutations_dicts = [dict(zip(keys, v)) for v in itertools.product(*values)]
    return permutations_dicts
