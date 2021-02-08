import typer

from .. import state
from .. import dispatch

from ..computation import local_cleaner

def clean(
    location: str = typer.Option("local", help=state.help_texts['location']),
):

    if location == 'local':
        clean_local()
    else:
        experiment_config = state.experiment_config
        location_type = experiment_config[location]
        if location_type == 'cluster':
            clean_cluster()


def clean_local():
    local_cleaner.clean()

def clean_cluster():
    pass
