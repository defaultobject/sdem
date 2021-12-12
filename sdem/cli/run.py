import typer

from .. import state
from .. import dispatch
from ..computation import manager, local_runner, docker_runner, cluster, server
from .. import utils


def run(
    location: str = typer.Option("local", help=state.help_texts["location"]),
    force_all: bool = typer.Option(True, help=state.help_texts["force_all"]),
    new_only: bool = typer.Option(False, help='Only run experiment that have no results'),
    observer: bool = typer.Option(True, help=state.help_texts["observer"]),
    filter: str = typer.Option("{}", help=state.help_texts["filter"]),
    filter_file: str = typer.Option(None, help=state.help_texts["filter_file"]),
    print_configs: bool = typer.Option(False, help="Print Found Configs"),
    sbatch: bool = typer.Option(
        True, help="If true will automatically call sbatch to run files on cluster"
    ),
):

    experiment_config = state.experiment_config

    # construct filter from passed input and file input
    filter_dict = manager.construct_filter(filter, filter_file)

    # group together params so passing them around is easier
    run_settings = {
        "observer": observer,
        "force_all": force_all,
        "run_sbatch": sbatch,
    }

    # load all experiment configs 
    configs_to_run = manager.get_configs_from_model_files(experiment_config)

    # remove configs that do not match filter
    configs_to_run = manager.filter_configs(configs_to_run, filter_dict, new_only)

    if print_configs:
        utils.print_dict(configs_to_run)

    # Run if not in dry mode
    if state.dry == False:
        fn = manager.get_dispatched_fn('run', location, experiment_config)
        fn(configs_to_run, experiment_config, run_settings, location)


@dispatch.register("run", "local")
def local_run(configs_to_run, experiment_config, run_settings, location):
    local_runner.local_run(configs_to_run, experiment_config, run_settings)


@dispatch.register("run", "docker")
def docker_run(configs_to_run, experiment_config, run_settings, location):
    docker_runner.docker_run(configs_to_run, run_settings)


@dispatch.register("run", "cluster")
def cluster_run(configs_to_run, experiment_config, run_settings, location):
    cluster.cluster_run(configs_to_run, run_settings, location)


@dispatch.register("run", "server")
def server_run(configs_to_run, experiment_config, run_settings, location):
    server.server_run(configs_to_run, run_settings, location)
