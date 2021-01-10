import typer

from .. import state
from .. import dispatch
from ..computation import manager
from .. import utils

def run(
    location: str = typer.Option("local", help=state.help_texts['location']),
    force_all: bool = typer.Option(True, help=state.help_texts['force_all']),
    filter: str = typer.Option("{}", help=state.help_texts['filter']),
    filter_file: str = typer.Option(None, help=state.help_texts['filter_file']),
):

    filter_dict = utils.str_to_dict(filter)

    filter_from_file = {}
    if filter_file is not None:
        #filter from file will overwrite filter_dict
        filter_from_file = utils.json_from_file(filter_file)

    filter_dict =  utils.add_dicts([filter_dict, filter_from_file])

    #group together params so passing them around is easier
    run_settings = {
        'force_all': force_all
    }

    #load experiment configs and filter
    configs_to_run = manager.get_configs_from_model_files()
    configs_to_run = manager.filter_configs(configs_to_run, filter_dict)

    #get relevant run function
    fn = dispatch.dispatch('run', location)

    fn(configs_to_run, run_settings)


@dispatch.register('run', 'local')
def local_run(configs_to_run, run_settings):
    print('local_ron')

@dispatch.register('run', 'docker')
def docker_run(configs_to_run, run_settings):
    print('docker_ron')


