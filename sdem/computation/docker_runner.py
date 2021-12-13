from loguru import logger

from .. import state
from .. import decorators
from . import docker, manager

import os


def docker_run(configs_to_run, experiment_config, run_settings):
    """
    Runs all experiments in experiments sequentially on the local machine
    These experiments will be run using a file storage observed which will be converted
        to a mongo entry after running.

    Args:
        configs_to_run: list of all experiment configs
    """

    observer_flag = run_settings["observer"]

    if state.verbose:
        if not (observer_flag):
            logger.info(f"Running without sacred observer")

    if observer_flag:
        run_command_tmpl = experiment_config['template']['run_command']['docker']
    else:
        run_command_tmpl = experiment_config['template']['run_command']['docker_no_observer']



    docker_config = experiment_config["docker"]
    docker_run_command = docker.get_docker_run_command(experiment_config, docker_config)

    for exp in configs_to_run:
        run_command = manager.substitute_config_in_str(
            run_command_tmpl,
            exp
        )

        run_exp_command = f' /bin/bash -c  "{run_command}"'
        run_command = docker_run_command + run_exp_command

        if state.verbose:
            logger.info(run_command)

        os.system(run_command)
