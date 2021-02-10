import typer

from .. import state
from .. import dispatch

from ..computation import local_cleaner, cluster

def clean(
    location: str = typer.Option("local", help=state.help_texts['location']),
):

    if location == 'local':
        clean_local(location)
    else:
        experiment_config = state.experiment_config
        location_type = experiment_config[location]['type']
        if location_type == 'cluster':
            clean_cluster(location)


def clean_local(location):
    local_cleaner.clean()

def clean_cluster(location):
    cluster.clean_up_cluster(location)
