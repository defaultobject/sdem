import dateutil.parser
import os
import argparse
import yaml
import json

import seml
import warnings
from loguru import logger

from . import  sacred_manager
from .. import state
from .. import dispatch
from .. import utils
from ..utils import get_permission, mkdir_if_not_exists, remove_dir_if_exists

def start_omniboard(experiment_name):
    """
        1) creates an omniboard directory, if it doesnt exist, to hold a DB config file.
        2) Sets OMNIBOARD_CONFIG environment to be able to find the the config file.
        3) Starts omniboard 
        4) resets OMNIBOARD_CONFIG

        
    """
    if state.verbose:
        logger.info('Starting omniboard')

    db_config = seml.database.get_mongodb_config()

    user=db_config['username']
    password=db_config['password']
    host=db_config['host']
    db_name = db_config['db_name']

    template = dispatch.dispatch('template', '')()
    tmp_dir = template['tmp_dir']

    omniboard_dir = f'{tmp_dir}/omniboard/'

    #if omniboard_dir already exists we need to check that we can delete it
    if os.path.isdir(omniboard_dir):

        ans = utils.get_permission(
            f'Omniboard direcotry already exists ({omniboard_dir}), overwrite?'
        )

        if ans is False:
            if state.verbose:
                logger.info('Cant overwrite so exiting')
            return

    #start omniboard
    mkdir_if_not_exists(tmp_dir)
    mkdir_if_not_exists(omniboard_dir)

    omniboard_config_dict = {
        'sacred_1': {
            'mongodbURI': "mongodb://{user}:{password}@{host}/{db_name}".format(password=password, user=user, host=host, db_name=db_name),
            'path': "/{name}".format(name='sacred'),
            'runsCollectionName': experiment_name+'_runs'
        }
    }

    with open(f'{omniboard_dir}/db_config.json', 'w') as fp:
        json.dump(omniboard_config_dict, fp)

    original_environ = None

    if 'OMNIBOARD_CONFIG'  in os.environ.keys():
        original_environ = os.environ["OMNIBOARD_CONFIG"]

    os.environ["OMNIBOARD_CONFIG"] = os.getcwd()+'{omniboard_dir}/db_config.json'

    #start omniboard
    os.system('omniboard')

    #omniboard now closed
    if state.verbose:
        logger.info('Closing down omniboard - cleaning up')

    #reset omniboard config
    if original_environ is None:
        del os.environ["OMNIBOARD_CONFIG"]
    else:
        os.environ["OMNIBOARD_CONFIG"] = original_environ


    #delete omniboard folder
    remove_dir_if_exists(f'{omniboard_dir}')

def start_sacredboard(experiment_name):
    db_config = seml.database.get_mongodb_config()
    user=db_config['username']
    password=db_config['password']
    host=db_config['host']
    db_name = db_config['db_name']

    mongodbURI =  "mongodb://{user}:{password}@{host}/{db_name}".format(password=password, user=user, host=host, db_name=db_name)

    os.system('sacredboard -mu {uri} {db_name} -mc {name}'.format(uri = mongodbURI, db_name=db_name, name=experiment_name))

