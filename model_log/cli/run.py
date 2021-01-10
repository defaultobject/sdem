import typer

from .. import config
from .. import dispatch

def run(
    name: str,
    location: str = typer.Option("local", help=config.help_texts['location']),
    force_all: bool = typer.Option(True, help=config.help_texts['force_all']),
):
    #group together params so passing them around is easier
    run_settings = {
        'force_all': force_all
    }

    #get relevant run function
    fn = dispatch.dispatch('run', location)

    fn(run_settings)


@dispatch.register('run', 'local')
def local_run(run_settings):
    print('local_ron')

@dispatch.register('run', 'docker')
def docker_run(run_settings):
    print('docker_ron')


