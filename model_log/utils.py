from pathlib import Path
import shutil
import typing
import os
import yaml
import itertools
import hashlib
import json
import uuid
import copy

import importlib
import importlib.util
from loguru import logger
import typing

YES_LIST = ('yes', 'true', 't', 'y', '1')
NO_LIST = ('no', 'false', 'f', 'n', '0')

def _s(*args) -> str:
    """
        *args: List[str]
    """
    s_arr = [str(s) for s in args]
    return ''.join(s_arr)

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

def json_from_file(f: str) -> dict:
    _dict = {}

    with open(f, 'r') as fh:
        _dict = json.load(fh)

    return _dict

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

def add_dicts(dict_array: typing.List[dict], deepcopy=False) -> dict:
    """
        Adds all dicts in dict_array into the first dict and returns this.
    """
    sum_dict = None
    for d in dict_array:
        if deepcopy:
            d = copy.deepcopy(d)

        if sum_dict is None:
            sum_dict = d
        else:
            sum_dict.update(d)

    return sum_dict

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


