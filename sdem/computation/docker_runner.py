from loguru import logger

from .. import state
from .. import decorators
from . import docker, manager

import os


def docker_run(state, configs_to_run, run_settings, location, docker_image = None):
    """
    Runs all experiments in experiments sequentially on the local machine
    These experiments will be run using a file storage observed which will be converted
        to a mongo entry after running.

    Args:
        configs_to_run: list of all experiment configs
    """

    experiment_config = state.experiment_config

    observer_flag = run_settings["observer"]

    if state.verbose:
        if not (observer_flag):
            logger.info(f"Running without sacred observer")

    if observer_flag:
        run_command_tmpl = experiment_config['template']['run_command']['docker']
    else:
        run_command_tmpl = experiment_config['template']['run_command']['docker_no_observer']

    docker_config = experiment_config[location]

    for i, exp in enumerate(configs_to_run):
        # copy dict
        docker_config_i = dict(docker_config)

        # arguments passed through cli have priority
        if docker_image is not None:
            docker_config_i['name'] = docker_image
        elif 'docker_image' in exp.keys():
            # then config has priority
            docker_config_i['name'] = exp['docker_image']
        else:
            #otherwise we use what is in the exerimenet config
            pass

        docker_run_command = docker.get_docker_run_command(experiment_config, docker_config_i)

        run_command = manager.substitute_config_in_str(
            run_command_tmpl,
            exp
        )

        run_exp_command = f' /bin/bash -c  "{run_command}"'
        run_command = docker_run_command + run_exp_command

        state.console.rule(f'Running experiment {i}')
        state.console.print(run_command, soft_wrap=True)

        os.system(run_command)
