import typer

from .. import state
from .. import dispatch
from ..computation import manager, cluster, mongo, server


def sync(location: str = typer.Option("local", help=state.help_texts["location"])):
    # load experiment configs and filter
    experiment_config = state.experiment_config

    # if cluster
    if location in experiment_config.keys():
        if experiment_config[location]["type"] == "cluster":
            fn = dispatch.dispatch("sync", "cluster")
        elif experiment_config[location]["type"] == "server":
            fn = dispatch.dispatch("sync", "server")
        else:
            # get relevant run function
            fn = dispatch.dispatch("sync", location)

    else:
        # get relevant run function
        fn = dispatch.dispatch("sync", location)

    fn(location)


@dispatch.register("sync", "local")
def local_sync(location):
    mongo.sync()


@dispatch.register("sync", "cluster")
def cluster_sync(location):
    cluster.sync_with_cluster(location)

@dispatch.register("sync", "server")
def cluster_sync(location):
    server.sync(location)
