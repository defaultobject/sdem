import dateutil.parser

import os

import argparse

import yaml
import json

import seml

from .util import add_dicts, mkdir_if_not_exists

from . import  sacred_manager, manager

from . import settings
from .sacred_vis import start_omniboard, start_sacredboard


from . import local
from . import cluster
from . import dvc_manager

def str2bool(v):
    #from https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
    if isinstance(v, bool):
       return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def arg_dict(v):
    return json.loads(v)

def argument_parser() -> dict:
    parser = argparse.ArgumentParser(description='Experiment running parser.')
    parser.add_argument('--location',  type=str, default='local', help='Location to run on. Either on local computer, or a cluster/server name. docker will run docker locally.')
    parser.add_argument('--config',  type=str, default='experiment_config.yaml', help='Path to experiment config file.')
    parser.add_argument('--force_all',  type=str2bool, default=True, help='Force all experiment to re run, otherwise will only run those that have not already completed.')
    parser.add_argument('--omniboard', help="Start omniboard", action="store_true")
    parser.add_argument('--sacredboard', help="Start sacredboard", action="store_true")
    parser.add_argument('--sync', help="Sync with location", action="store_true")
    parser.add_argument('--clean', help="Clean up unneeded files", action="store_true")
    parser.add_argument('--dry', help="Dry run flag", action="store_true")
    parser.add_argument('--check', help="Check status of experiments on cluster", action="store_true")
    parser.add_argument('--dvc-push', help="Clean up and push experiments to DVC storage", action="store_true")
    parser.add_argument('--dvc-pull', help="Clean up and get experiments from DVC storage", action="store_true")
    parser.add_argument('-v', help="increase output verbosity", action="store_true")
    parser.add_argument('--prune_unfinished', help="remove all experiments that did not finish", action="store_true")
    parser.add_argument('--no_observer', help="Do not add a sacred observer to the experiment", action="store_true")

    parser.add_argument('--filter',  type=arg_dict, default={}, help='Filter experiment to run. Default is {} so it does not filter.')
    parser.add_argument('--filter_file',  type=str, default=None, help='Filter experiment by json file.')
    parser.add_argument('--run_file',  type=str, default=None, help='Run a file at a specific location')

    args = parser.parse_args()

    return vars(args) #return an dict

def get_experiment_config(file_path: str, run_location:str) -> dict:
    """
        Experiments have two config dicts, one that describes the config and one that describes the run locations.
        Return both.
    """
    _dict = {}
    with open(file_path, 'r') as stream:
        try:
            _dict = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
            raise exc

    if run_location not in _dict.keys():
        raise RunTimeError('No config for run location {f} found'.format(f=run_location))

    if 'experiment' not in _dict.keys():
        raise RunTimeError('Experiment config not found')

    run_dict =  _dict[run_location]
    experiment_dict =  _dict['experiment']

    if run_dict is None:
        #where there are no keys in the yaml item run_dict will be None
        return {}

    if experiment_dict is None:
        return {}

    return experiment_dict, run_dict

def check_if_proper_run_config(config):
    if 'type' not in config.keys():
        raise 'type key should be in config'

def check_if_proper_experiment_config(config):
    pass

def merge_parser_config(config, args):
    return add_dicts([config, args])

def add_experiment_config_defaults(config: dict) -> dict:
    default = {
        'use_config_id': True,
        'overwrite_id': True,
        'mongo_observer': True, #if false will use a file storage observer
    }

    for k, v in default.items():
        if k not in config:
            config[k] = v

    return config
  
def print_config(config):
    print(json.dumps(config, sort_keys=True, indent=3))


def run_file(experiments, experiment_config, run_config):
    if run_config['type'] == 'local':
        local.run_file(experiment_config, run_config)
    pass

def run_experiments(experiments, experiment_config, run_config):
    """
        experiments: array of experiments configs to run
        experiment_config (dict): describes the configuration of how to run experiments
        run_config (dict): describes the configuration of place where the experiments will run
    """
    experiment_name = experiment_config['experiment_name']
    collection = experiment_config['collection']

    sacred_manager.queue_runs(experiment_name, collection, experiments)

    if run_config['type'] == 'local':
        local.run_experiments(experiments, experiment_config, run_config)

        if experiment_config['no_observer'] == False:
            manager.sync_filestorage_with_mongo(experiment_config, run_config)
    elif run_config['type'] == 'cluster':
        #we do not know when the cluster finishes so we will sync separately
        cluster.run_experiments(experiments, experiment_config, run_config)
    else:
        raise NotImplementedError('Run type {t} has not been implemented'.format(t=run_config['type']))

def sync_experiments(experiment_config, run_config):
    #nothing to do if localhost

    if run_config['type'] == 'local':
        manager.sync_filestorage_with_mongo(experiment_config, run_config)
    elif run_config['type'] == 'cluster':
        cluster.sync_with_cluster(experiment_config, run_config)
        manager.sync_filestorage_with_mongo(experiment_config, run_config)

def check_experiments(experiment_config, run_config):
    if run_config['type'] == 'cluster':
        cluster.check_experiments(experiment_config, run_config)

def ask_permission(question, fn):
        ans = input(question)
        if ans == '1' or ans == 'y' or ans == 'yes':
            fn()

def clean_up(experiment_config, run_config):
    experiment_name = experiment_config['experiment_name']
    if run_config['type'] == 'cluster':
        ask_permission(
            'Delete experiment {name} on cluster?'.format(name=experiment_name),
            lambda: cluster.clean_up_cluster(experiment_config, run_config)
        )

    elif run_config['type'] == 'local':
        """
            Local clean up
                - syncs with mongo
                - removes experiment files that are not in mongo and renames ids to match order_id
                - removes untracked artifacts and sources from mongodb
                - remove any cluster temp files
        """

        ask_permission(
            'Sync local files with mongo?',
            lambda: manager.sync_filestorage_with_mongo(experiment_config, run_config)
        )
        ask_permission(
            'Prune experiment files and fix IDs?',
            lambda: manager.prune_and_fix_experiment_ids(experiment_config, run_config)
        )
        ask_permission(
            'Re-sync local files with mongo?',
            lambda: manager.sync_filestorage_with_mongo(experiment_config, run_config)
        )
        ask_permission(
            'Remove untracked mongo files?',
            lambda: sacred_manager.cleanup(experiment_config['experiment_name'])
        )
        ask_permission(
            'Remove cluster temp files?',
            lambda: cluster.clean_up_temp_files(experiment_config, run_config)
        )

def prune_unfinished(experiment_config, run_config):
    ask_permission(
        'Remove failed experiments?',
        lambda: manager.prune_unfinished(experiment_config, run_config)
    )

def get_experiments(experiment_config, run_config):
    experiments_configs_to_run = manager.get_filtered_configs_from_model_files(experiment_config['filter'])
    if experiment_config['force_all']:
        #return all experiments
        return experiments_configs_to_run
    else:
        #return experiments that are not is sacred DB and those are a in the DB but are not completed
        collection = experiment_config['collection']

        sacred_ids = sacred_manager.get_sacred_ids_of_configs(
            collection,
            experiments_configs_to_run,
            drop_global_id=True
        )

        sacred_ids_to_run = sacred_manager.get_ids_to_run(experiment_config, collection)

        _experiments_configs_to_run = []
        for i, _id in enumerate(sacred_ids):
            if len(_id) > 1:
                raise RuntimeError('Number of ids matched must not be greater than 1: ', _id)

            if len(_id) == 0:
                #not in db, so run
                _experiments_configs_to_run.append(experiments_configs_to_run[i])

            if len(_id) == 1:
                if _id in sacred_ids_to_run:
                    _experiments_configs_to_run.append(experiments_configs_to_run[i])


        experiments_configs_to_run = _experiments_configs_to_run
        return experiments_configs_to_run


def run():
    """
        This sets off running the results either locally, or externally. First the experiments to run are found and then these are set off.
    """
    args = argument_parser()
    verbose_flag = args['v']


    settings.verbose_flag = verbose_flag

    experiment_name = sacred_manager.get_experiment_name()

    if args['omniboard']:
        start_omniboard(experiment_name)
        return
    elif args['sacredboard']:
        start_sacredboard(experiment_name)
        return


    experiment_dict, run_config = get_experiment_config(args['config'], args['location'])


    check_if_proper_run_config(run_config)
    check_if_proper_experiment_config(experiment_dict)

    experiment_config = merge_parser_config(experiment_dict, args)
    experiment_config = add_experiment_config_defaults(experiment_config)

    if verbose_flag:
        #must print before adding collection because collection is not seriablable
        print('==============EXPERIMENT DICT==============')
        print_config(experiment_config)
        print('==============RUN DICT==============')
        print_config(run_config)

    collection = sacred_manager.get_experiments_collection()

    experiment_config['experiment_name'] = experiment_name
    experiment_config['collection'] = collection

    if args['filter_file'] is not None:
        with open(args['filter_file'], 'r') as fh:
            filter_dict = json.load(fh)

        experiment_config['filter'] = filter_dict
    else:
        experiment_config['filter'] = args['filter']

    if args['sync']:
        sync_experiments(experiment_config, run_config)
        return
    elif args['clean']:
        clean_up(experiment_config, run_config)
        return
    elif args['dvc_push']:
        clean_up(experiment_config, run_config)
        dvc_manager.save_to_storage()
        return
    elif args['dvc_pull']:
        clean_up(experiment_config, run_config)
        dvc_manager.get_from_storage()
        ask_permission(
            'Re-sync local files with mongo?',
            lambda: manager.sync_filestorage_with_mongo(experiment_config, run_config)
        )
        return
    elif args['check']:
        check_experiments(experiment_config, run_config)
        return
    elif args['prune_unfinished']:
        prune_unfinished(experiment_config, run_config)
        return

    experiments_configs_to_run = get_experiments(experiment_config, run_config)

    if settings.verbose_flag:
        print('running ', len(experiments_configs_to_run),' experiments')

    if not args['dry']:
        if args['run_file']:
            run_file(experiments_configs_to_run, experiment_config, run_config)
        else:
            run_experiments(experiments_configs_to_run, experiment_config, run_config)




