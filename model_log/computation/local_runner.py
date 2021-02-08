from loguru import logger

from .. import state
from .. import decorators


@decorators.run_if_not_dry
def local_run(configs_to_run, run_settings):
    """
        Runs all experiments in experiments sequentially on the local machine
        These experiments will be run using a file storage observed which will be converted 
            to a mongo entry after running.
    """


    for exp in configs_to_run:
        name = exp['filename']
        order_id = exp['order_id']

        if state.verbose:
            logger.info(f'Running experiment {name} {order_id}')

    pass
