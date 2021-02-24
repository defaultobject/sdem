from loguru import logger

from .. import state
from .. import decorators
from . import docker

import os

RUN_COMMAND = "cd models; python {name} {order} {observer}"


@decorators.run_if_not_dry
def docker_run(configs_to_run, run_settings):
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

    observer_flag = int(run_settings["observer"])

    docker_config = state.experiment_config["docker"]
    docker_run_command = docker.get_docker_run_command(docker_config)

    for exp in configs_to_run:
        name = exp["filename"]
        order_id = exp["order_id"]

        if state.verbose:
            logger.info(f"Running experiment {name} {order_id}")

        run_command = RUN_COMMAND.format(
            name=name, order=order_id, observer=observer_flag
        )
        run_command = "cd /home/app; " + run_command

        run_exp_command = f' /bin/bash -c  "{run_command}"'
        run_command = docker_run_command + run_exp_command

        os.system(run_command)
