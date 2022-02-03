import typer

from .. import state
from .. import dispatch

from ..computation import local_cleaner, cluster, manager


def clean(
    ctx: typer.Context,
    location: str = typer.Option("local", help=state.help_texts["location"]),
):
    state = ctx.obj
    experiment_config = state.experiment_config

    if state.dry == False:
        fn = manager.get_dispatched_fn('clean', location, experiment_config)
        fn(state, location)


@dispatch.register("clean", "local")
def clean_local(state, location):
    state.console.rule(f'Cleaning locally')
    local_cleaner.clean(state)


@dispatch.register("clean", "cluster")
def clean_cluster(state, location):
    state.console.rule(f'Cleaning cluster -- {location}')
    cluster.clean_up_cluster(location, state)
