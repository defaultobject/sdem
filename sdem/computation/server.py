from loguru import logger

from .. import state
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

@decorators.run_if_not_dry
def server_run(configs_to_run, run_settings, location):
    experiment_config = state.experiment_config
    cluster_config = experiment_config[location]
    experiment_name = manager.get_experiment_name()

    if cluster.check_if_experiment_exists_on_cluster(experiment_name, cluster_config):
        if state.verbose:
            logger.info(f"Experiment is already on server - {location}, exiting!")

        return None

    
    #make sure jobs folder exists
    Path('jobs').mkdir(exist_ok=True)

    cluster.compress_files_for_cluster(
        configs_to_run, run_settings, experiment_name, cluster_config
    )
    cluster.move_files_to_cluster(configs_to_run, run_settings, experiment_name, cluster_config)


@decorators.run_if_not_dry
def sync(location):
    cluster.sync_with_cluster(location)

