import typer

from .. import state
from .. import dispatch
from ..computation import manager, cluster, mongo, server


def sync(ctx: typer.Context, location: str = typer.Option("local", help=state.help_texts["location"])):
    state = ctx.obj
    experiment_config = state.experiment_config

    fn = manager.get_dispatched_fn('sync', location, experiment_config)

    fn(state, location)


@dispatch.register("sync", "local")
def local_sync(location):
    raise NotImplementedError()
    #mongo.sync()


@dispatch.register("sync", "cluster")
def cluster_sync(state, location):
    state.console.rule(f'Syncing with cluster -- {location}')
    cluster.sync_with_cluster(state, location)

@dispatch.register("sync", "server")
def cluster_sync(state, location):
    raise NotImplementedError()
    server.sync(location)
