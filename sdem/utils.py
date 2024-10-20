from pathlib import Path
import shutil
import typing
import os
import sys
import yaml
import itertools
import hashlib
import json
import uuid
import copy
import numpy as np
from collections.abc import Iterable

import importlib
import importlib.util
from loguru import logger
import typing
import zipfile

import pickle



YES_LIST = ("yes", "true", "t", "y", "1")
NO_LIST = ("no", "false", "f", "n", "0")



def _s(*args) -> str:
    """ 
    Concate all args. Notation follows from numpy np._c[]
        *args: List[str] 
    """
    s_arr = [str(s) for s in args]
    return "".join(s_arr)

def save_to_pickle(data, name):
    """ Save data to a pickle under the file path name"""
    with open(name, 'wb') as file:
        pickle.dump(data, file)

def read_pickle():
    raise NotImplementedError()


def is_bool_str(v: str) -> bool:
    if (v.lower() in YES_LIST)or v.lower() in NO_LIST :
        return True
    return False

def str_to_bool(v: str) -> bool:
    """
    Convert string input to a boolean
        from https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    """
    if isinstance(v, bool):
        return v
    if v.lower() in YES_LIST:
        return True
    elif v.lower() in NO_LIST:
        return False
    else:
        raise RuntimeError("Boolean value expected.")

def str_to_dict(s: str) -> dict:
    """ Convert input into a dict """
    return json.loads(s)


@logger.catch(reraise=True)
def json_from_file(f: str) -> dict:
    """ Read a json file into a dict """
    _dict = {}

    with open(f, "r") as fh:
        _dict = json.load(fh)

    return _dict


def get_permission(question):
    """ Ask user for yes or no """
    ans = input(question)
    if ans in YES_LIST:
        return True
    return False


def ask_permission(question, fn=None):
    """ Ask permission before running fn """
    ans = get_permission(question)

    if fn is None:
        return ans
    else:
        if ans:
            fn()


def move_dir_if_exists(root: Path, tmp_dir: Path) -> None:
    """ If root exists move root to tmp_dir.  """
    if root.exists():
        # TODO: rewrite using pathlib
        shutil.move(str(root), str(tmp_dir))


def mkdir_if_not_exists(root):
    Path(root).mkdir(exist_ok=True)


def remove_dir_if_exists(root):
    if os.path.exists(root):
        shutil.rmtree(root)


def delete_if_empty(d):
    if len(os.listdir(d)) == 0:
        remove_dir_if_exists(d)


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
    is_subset = True
    for k, i in dict1.items():
        if k not in dict2.keys():
            is_subset = False
            break

        if type(i) is list:
            # if is a list then either the element is a list or we need to sum over the list
            if type(dict2[k]) is list:
                # matching lists
                if dict2[k] != dict1[k]:
                    is_subset = False
                    break

            else:
                # loop through dict1 and check if any match
                any_matched = False
                for item in dict1[k]:
                    if dict2[k] == item:
                        any_matched = True
                        break
                if not any_matched:
                    is_subset = False
                    break
        else:
            if dict1[k] != dict2[k]:
                is_subset = False
                break

    return is_subset


def get_dict_without_key(_dict, key):
    return {i: _dict[i] for i in _dict if i != key}


def get_dict_hash(_dict):
    """
    Args:
        _dict (dict) - a single configuration
    Returns:
        md5 hash of the sorted _dict
    """
    return hashlib.md5(json.dumps(_dict, sort_keys=True).encode("utf-8")).hexdigest()


def get_unique_key():
    """ Return a unique global ID """
    return uuid.uuid4().hex


def load_mod(file_path: Path):
    """
    loads file_name as a python module
    """
    parent_dir = str(file_path.parent.resolve())
    file_name = file_path.name

    # store current directory so we can return later
    cwd = os.getcwd()

    # cd into root so that relative paths inside file_name still work
    os.chdir(parent_dir)

    spec = importlib.util.spec_from_file_location("", file_name)
    foo = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(foo)

    # revert back to orginal working directory
    os.chdir(cwd)

    return foo


def read_yaml(file_name):
    # load experiment config
    with open(file_name) as f:
        # The FullLoader parameter handles the conversion from YAML
        # scalar values to Python the dictionary format
        ec = yaml.load(f, Loader=yaml.FullLoader)

    return ec


class Split():
    pass

def get_all_permutations(options):
    # python passes dicts around by reference, this can cause some issues as we are looping over the dicts and editing them
    # therefore create a deep copy to break the reference
    options = copy.deepcopy(options)

    if type(options) is list:
        dict_list = []
        for opt in options:
            dict_list = dict_list + get_all_permutations(opt)

        return dict_list
    else:
        # check if any Split keys
        if any([isinstance(k, Split) for k in options.keys()]):
            # for each split we construct an array of configs, one for each element in the split
            # We recursively apply split each element

            option_list = []

            options_copy = copy.deepcopy(options)

            for k in options_copy.keys():
                if isinstance(k, Split):
                    # split
                    config_to_split = options_copy.pop(k)
                    for _config in config_to_split:
                        new_config = add_dicts(
                            [
                                options_copy,
                                _config
                            ],
                            deepcopy=True
                        )
                        option_list.append(new_config)

                    break

            return get_all_permutations(option_list)
        else:
            # get all permutations of options
            keys, values = zip(*options.items())
            permutations_dicts = [dict(zip(keys, v)) for v in itertools.product(*values)]
            return permutations_dicts


def zip_dir(path, zipf, ignore_dir_arr=None, dir_path=None):
    """
    Path can be something like ../../folder_1/folder_2/lib/*
    we strip all leading directory structure and zip only lib/*
    """
    # target_dir = os.path.basename(os.path.normpath(path))

    path_split = os.path.normpath(path).split(os.sep)

    if dir_path is None:
        dir_path = ""

    for root, dirs, files in os.walk(path):
        for folder_name in dirs:
            if ignore_dir_arr is not None:
                ignore_flag = False
                for ignore_dir in ignore_dir_arr:
                    # if the root starts with ignore dir then we do not want to zip it
                    if str(root).startswith(ignore_dir):
                        ignore_flag = True
                if ignore_flag:
                    # do not zip this dir
                    continue

            # remove leading directory structure
            root_split = os.path.normpath(root).split(os.sep)
            if dir_path:
                target_dir = dir_path
            else:
                target_dir = os.path.join(*root_split[(len(path_split) - 1) :])

            zipf.write(
                os.path.join(root, folder_name), os.path.join(target_dir, folder_name)
            )

        for f in files:
            if ignore_dir_arr is not None:
                ignore_flag = False
                for ignore_dir in ignore_dir_arr:
                    # if the root starts with ignore dir then we do not want to zip it
                    if str(root).startswith(ignore_dir):
                        ignore_flag = True
                if ignore_flag:
                    # do not zip this dir
                    continue

            # remove leading directory structure
            root_split = os.path.normpath(root).split(os.sep)
            if dir_path:
                target_dir = dir_path
            else:
                target_dir = os.path.join(*root_split[(len(path_split) - 1) :])

            zipf.write(os.path.join(root, f), str(os.path.join(target_dir, f)))


def ensure_backslash(s):
    if s[-1] != "/":
        return s + "/"
    return s

def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text  


def process_unknown_kwarg_var(v):
    if is_bool_str(v):
        return str_to_bool(v)
    return v

def pass_unknown_kargs(unknown_args) -> dict:
    if len(unknown_args) == 0:
        return {}

    # TODO: check that input is correct
    ind = list(range(int(len(unknown_args)/2))) 
    return {
        remove_prefix(unknown_args[i*2], '--'): process_unknown_kwarg_var(unknown_args[(i*2)+1] )
        for i in ind
    }

def flatten(xs):
    """
    Flatten a mixed-depth list into a single depth flat list 
    Supports: lists, numpy array, jax arrays
    """
    res = []
    for i in xs:
        # convert jax arrays to numpy array
        if type(i).__name__ == 'DeviceArray':
            i = np.array(i)

        # convery any numpy arrays to lists
        if isinstance(i, np.ndarray):
            i = i.tolist()

        if isinstance(i, Iterable):
            res = res + flatten(i)
        else:
            res.append(i)
    
    return res

