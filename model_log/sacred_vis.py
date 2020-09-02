import dateutil.parser

import os

import argparse

import yaml
import json

import seml

from .util import add_dicts, mkdir_if_not_exists

from . import  sacred_manager, manager

from . import settings

import warnings

def start_omniboard(experiment_name):
    """
        1) creates an omniboard directory, if it doesnt exist, to hold a DB config file.
        2) Sets OMNIBOARD_CONFIG environment to be able to find the the config file.
        3) Starts omniboard 
        4) resets OMNIBOARD_CONFIG

        
    """
    warnings.warn('Omniboard does not seem to work unless using the runs collection -- hopefully omniboard will fix this soon!')

    db_config = seml.database.get_mongodb_config()

    user=db_config['username']
    password=db_config['password']
    host=db_config['host']
    db_name = db_config['db_name']

    mkdir_if_not_exists('omniboard/')

    omniboard_config_dict = {
        'sacred_1': {
            'mongodbURI': "mongodb://{user}:{password}@{host}/{db_name}".format(password=password, user=user, host=host, db_name=db_name),
            'path': "/{name}".format(name='sacred'),
            'runsCollectionName': experiment_name+'_runs'
        }
    }

    with open('omniboard/db_config.json', 'w') as fp:
        json.dump(omniboard_config_dict, fp)

    original_environ = None
    if 'OMNIBOARD_CONFIG'  in os.environ.keys():
        original_environ = os.environ["OMNIBOARD_CONFIG"]

    os.environ["OMNIBOARD_CONFIG"] = os.getcwd()+'/omniboard/db_config.json'
    print(os.getcwd()+'/omniboard/db_config.json')

    os.system('omniboard')

    if settings.verbose_flag:
        print('closing down')

    if True:
        if original_environ is None:
            del os.environ["OMNIBOARD_CONFIG"]
        else:
            os.environ["OMNIBOARD_CONFIG"] = original_environ

def start_sacredboard(experiment_name):
    db_config = seml.database.get_mongodb_config()
    user=db_config['username']
    password=db_config['password']
    host=db_config['host']
    db_name = db_config['db_name']

    mongodbURI =  "mongodb://{user}:{password}@{host}/{db_name}".format(password=password, user=user, host=host, db_name=db_name)

    os.system('sacredboard -mu {uri} {db_name} -mc {name}'.format(uri = mongodbURI, db_name=db_name, name=experiment_name))

