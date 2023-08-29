from loguru import logger

from .. import decorators
from .. import template
from .. import utils
from . import manager

import os

import shutil
import zipfile
import subprocess
from pathlib import Path

from . import cluster

def make_run_file(state, configs_to_run, run_settings, experiment_name, experiment_config, cluster_config):

    run_template = cluster_config['run_command']

    fname = Path(f'jobs/run_{experiment_name}.sh')

    if fname.exists():
        fname.unlink()

    with open (fname, 'w') as rsh:
        for config in configs_to_run:
            rsh.writelines(
                run_template.format(
                    experiment_name=experiment_name,
                    filename=config['filename'],
                    order_id=config['order_id'],
                )+ '\n'
            ) 

    return fname

def server_run(state, configs_to_run, run_settings, location):
    experiment_config = state.experiment_config
    cluster_config = cluster.get_cluster_config(experiment_config, location)
    experiment_name = manager.get_experiment_name(experiment_config)

    if run_settings['check_cluster']:
        if cluster.check_if_experiment_exists_on_cluster(experiment_name, cluster_config):
            if state.verbose:
                logger.info(f"Experiment is already on server - {location}, exiting!")

            return None

    
    #make sure jobs folder exists
    Path('jobs').mkdir(exist_ok=True)

    # make run file
    run_file: Path  = make_run_file(state, configs_to_run, run_settings, experiment_name, experiment_config, cluster_config)

    # add run file to be synced

    cluster.compress_files_for_cluster(
        state, configs_to_run, run_settings, experiment_name, cluster_config
    )
    cluster.move_files_to_cluster(state, configs_to_run, run_settings, experiment_name, cluster_config)


def sync(location):
    cluster.sync_with_cluster(state, location)

