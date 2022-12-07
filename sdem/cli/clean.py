import typer

from .. import state
from .. import dispatch

from ..computation import local_cleaner, cluster, manager


def clean(
    ctx: typer.Context,
    location: str = typer.Option("local", help=state.help_texts["location"]),
    delete_all: bool = typer.Option(False, help="Delete all experiments")
):
    state = ctx.obj
    experiment_config = state.experiment_config

    if state.dry == False:
        fn = manager.get_dispatched_fn('clean', location, experiment_config)
        fn(state, location, delete_all)


@dispatch.register("clean", "local")
def clean_local(state, location, delete_all):
    state.console.rule(f'Cleaning locally')
    local_cleaner.clean(state, delete_all)


@dispatch.register("clean", "cluster")
def clean_cluster(state, location, delete_all):
    state.console.rule(f'Cleaning cluster -- {location}')
    cluster.clean_up_cluster(location, state)
