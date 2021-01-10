from pathlib import Path
import shutil
import typing
import os
import yaml
import itertools
import hashlib
import json
import uuid

import importlib
import importlib.util
from loguru import logger

YES_LIST = ('yes', 'true', 't', 'y', '1')
NO_LIST = ('no', 'false', 'f', 'n', '0')

def str_to_bool(v: str) -> bool:
    #from https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    if isinstance(v, bool):
       return v
    if v.lower() in YES_LIST:
        return True
    elif v.lower() in NO_LIST:
        return False
    else:
        raise RuntimeError('Boolean value expected.')

def str_to_dict(s: str) -> dict:
    return json.loads(s)

def get_permission(question):
    ans = input(question)
    if ans in YES_LIST:
        return True
    return False

def ask_permission(question, fn):
    #Ask permission before running fn
    ans = get_permission(question)
    if ans:
        fn()

def mkdir_if_not_exists(root):
    Path(root).mkdir(exist_ok=True)

def remove_dir_if_exists(root):
    if os.path.exists(root):
        shutil.rmtree(root)

def split_path(path: str):
    return os.path.normpath(path).split(os.path.sep)

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

def get_unique_key():
    return uuid.uuid4().hex

def load_mod(root, file_name):
    """ 
        loads file_name as a python module
    """
    cwd = os.getcwd()
    #cd into root so that relative paths inside file_name still work
    os.chdir(root)
    spec = importlib.util.spec_from_file_location("", file_name)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    #revert back to orginal working directory
    os.chdir(cwd)
    return foo

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

