from loguru import logger

from .. import state
from .. import decorators

import os

RUN_COMMAND = "cd models; python {name} {order} {observer}"


@decorators.run_if_not_dry
def local_run(configs_to_run, run_settings):
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
        observer_flag = ''
    else:
        observer_flag = '--dry'

    for exp in configs_to_run:
        name = exp["filename"]
        order_id = exp["order_id"]

        if state.verbose:
            logger.info(f"Running experiment {name} {order_id}")

        run_command = RUN_COMMAND.format(
            name=name, order=order_id, observer=observer_flag
        )

        os.system(run_command)
