from loguru import logger
from typing import List

from .. import state
from .. import decorators
from . import manager

import os

RUN_COMMAND = "cd models; python {name} {order} {observer}"


def local_run(state: 'State', configs_to_run: List[dict], run_settings: dict) -> None:
    """
    Runs all experiments in experiments sequentially on the local machine
    These experiments will be run using a file storage observed which will be converted
        to a local entry after running.

    Args:
        configs_to_run: list of all experiment configs
    """

    experiment_config = state.experiment_config

    observer_flag = run_settings["observer"]

    if state.verbose:
        if not (observer_flag):
            state.console.log(f"Running without sacred observer")

    # Get correct run command for if a sacred observer is being used or not
    if observer_flag:
        run_command_tmpl = experiment_config['template']['run_command']['local']
    else:
        run_command_tmpl = experiment_config['template']['run_command']['local_no_observer']

    # Seqentially loop through each experiment
    for exp in configs_to_run:

        # Create command from the model config
        run_command = manager.substitute_config_in_str(
            run_command_tmpl,
            exp
        )

        if state.verbose:
            state.console.rule(f'Running {run_command}')

        os.system(run_command)

    state.console.print('[bold green]Finished[/]')
