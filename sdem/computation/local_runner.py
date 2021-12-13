from loguru import logger
from typing import List

from .. import state
from .. import decorators
from . import manager

import os

RUN_COMMAND = "cd models; python {name} {order} {observer}"


def local_run(configs_to_run: List[dict], experiment_config: dict, run_settings: dict) -> None:
    """
    Runs all experiments in experiments sequentially on the local machine
    These experiments will be run using a file storage observed which will be converted
        to a local entry after running.

    Args:
        configs_to_run: list of all experiment configs
    """

    observer_flag = run_settings["observer"]

    if state.verbose:
        if not (observer_flag):
            logger.info(f"Running without sacred observer")

    if observer_flag:
        run_command_tmpl = experiment_config['template']['run_command']['local']
    else:
        run_command_tmpl = experiment_config['template']['run_command']['local_no_observer']

    for exp in configs_to_run:
        run_command = manager.substitute_config_in_str(
            run_command_tmpl,
            exp
        )

        if state.verbose:
            print(f'Running {run_command}')

        os.system(run_command)
