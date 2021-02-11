import typer

from .. import state
from .. import dispatch
from ..computation import manager, local_runner, docker_runner, cluster
from .. import utils

def construct_filter(_filter, filter_file):
    filter_dict = utils.str_to_dict(_filter)

    filter_from_file = {}
    if filter_file is not None:
        #filter from file will overwrite filter_dict
        filter_from_file = utils.json_from_file(filter_file)

    filter_dict =  utils.add_dicts([filter_dict, filter_from_file])
    return filter_dict

def run(
    location: str = typer.Option("local", help=state.help_texts['location']),
    force_all: bool = typer.Option(True, help=state.help_texts['force_all']),
    observer: bool = typer.Option(True, help=state.help_texts['observer']),
    filter: str = typer.Option("{}", help=state.help_texts['filter']),
    filter_file: str = typer.Option(None, help=state.help_texts['filter_file']),
    sbatch: bool = typer.Option(True, help='If true will automatically call sbatch to run files on cluster'),
):

    #construct filter from passed input and file input
    filter_dict = construct_filter(filter, filter_file)
    
    #group together params so passing them around is easier
    run_settings = {
        'observer': observer,
        'force_all': force_all,
        'run_sbatch': sbatch,
    }

    #load experiment configs and filter
    configs_to_run = manager.get_configs_from_model_files()
    configs_to_run = manager.filter_configs(configs_to_run, filter_dict)

    experiment_config = state.experiment_config

    #if cluster 
    if location in experiment_config.keys():
        if experiment_config[location]['type'] == 'cluster':
            fn = dispatch.dispatch('run', 'cluster')
        else:
            #get relevant run function
            fn = dispatch.dispatch('run', location)
    else:
        #get relevant run function
        fn = dispatch.dispatch('run', location)

    fn(configs_to_run, run_settings, location)


@dispatch.register('run', 'local')
def local_run(configs_to_run, run_settings, location):
    local_runner.local_run(configs_to_run, run_settings)

@dispatch.register('run', 'docker')
def docker_run(configs_to_run, run_settings, location):
    docker_runner.docker_run(configs_to_run, run_settings)

@dispatch.register('run', 'cluster')
def cluster_run(configs_to_run, run_settings, location):
    cluster.cluster_run(configs_to_run, run_settings, location)


