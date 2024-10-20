import typer
from typing import List

from .. import dispatch
from ..computation import manager, local_runner, docker_runner, cluster, server
from .. import utils
from ..state import help_texts


def run(
    ctx: typer.Context,
    location: str = typer.Option("local", help=help_texts["location"]),
    force_all: bool = typer.Option(True, help=help_texts["force_all"]),
    new_only: bool = typer.Option(False, help='Only run experiment that have no results'),
    observer: bool = typer.Option(True, help=help_texts["observer"]),
    filter: str = typer.Option("{}", help=help_texts["filter"]),
    filter_file: str = typer.Option(None, help=help_texts["filter_file"]),
    print_configs: bool = typer.Option(False, help="Print Found Configs"),
    sbatch: bool = typer.Option(
        True, help="If true will automatically call sbatch to run files on cluster"
    ),
    check: bool = typer.Option(
        True, help="Check if files are on cluster cluster"
    ),
    ignore: List[str] = typer.Option([], help="List of file to not get configs from."),
    limit: int = typer.Option(None, help="Limit number of runs"),
    docker_image: str = typer.Option(None, help="Optional docker image")
):
    
    state = ctx.obj

    state.console.rule('Running experiments')

    experiment_config = state.experiment_config

    # construct filter from passed input and file input
    filter_dict = manager.construct_filter(filter, filter_file)

    if filter_dict != [{}]:
        # if non-empty print
        state.console.print('Only running experiments with:')
        state.console.print(filter_dict)

    # group together params so passing them around is easier
    run_settings = {
        "observer": observer,
        "force_all": force_all,
        "run_sbatch": sbatch,
        "check_cluster": check,
    }

    # load all experiment configs 
    configs_to_run = manager.get_configs_from_model_files(state, ignore_files=ignore)


    # remove configs that do not match filter
    configs_to_run = manager.filter_configs(state, configs_to_run, filter_dict, new_only)

    if limit is not None:
        state.console.print(f'Limiting to {limit} experiments')
        configs_to_run = configs_to_run[:limit]

    if len(configs_to_run) == 0:
        state.console.print('[bold red]No configs found to run! -- Exiting![/]')
        exit()
    else:
        state.console.print(f'Running {len(configs_to_run)} experiments!')

    if print_configs:
        state.console.print(configs_to_run)

    # Run if not in dry mode
    if state.dry == False:
        # We use dispatch to get the corresponding run function so that users can overwrite
        #   and add there own functions

        fn = manager.get_dispatched_fn('run', location, experiment_config)

        if location == 'docker':
            fn(state, configs_to_run, run_settings, location, docker_image=docker_image)
        else:
            fn(state, configs_to_run, run_settings, location)


@dispatch.register("run", "local")
def local_run(state, configs_to_run, run_settings, location):
    state.console.rule('Running locally')
    local_runner.local_run(state, configs_to_run, run_settings)


@dispatch.register("run", "docker")
def docker_run(state, configs_to_run, run_settings, location, docker_image = None):
    state.console.rule(f'Running on docker -- {location}')
    docker_runner.docker_run(state, configs_to_run, run_settings, location, docker_image)

@dispatch.register("run", "cluster")
def cluster_run(state, configs_to_run, run_settings, location):
    state.console.rule(f'Running on cluster {location}')
    cluster.cluster_run(state, configs_to_run, run_settings, location)


@dispatch.register("run", "server")
def server_run(state, configs_to_run, run_settings, location):
    state.console.rule('Running on server')
    server.server_run(state, configs_to_run, run_settings, location)
