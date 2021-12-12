import typer

from .. import state
from .. import dispatch

from ..computation import local_cleaner, cluster, manager


def clean(
    location: str = typer.Option("local", help=state.help_texts["location"]),
):
    experiment_config = state.experiment_config

    if state.dry == False:
        fn = manager.get_dispatched_fn('clean', location, experiment_config)
        fn(experiment_config, location)


@dispatch.register("clean", "local")
def clean_local(experiment_config, location):
    local_cleaner.clean(experiment_config)


@dispatch.register("clean", "cluster")
def clean_cluster(experiment_config, location):
    cluster.clean_up_cluster(location, experiment_config)
