""" Entry point to the sdem cli.  """
import typer

from . import state  # global settings
from . import template

from .computation import startup

from .cli import run, dvc, clean, vis, sync, setup, rollback, install, info
import warnings

from time import sleep

commands_no_start_up_check = ["setup", "install"]

app = typer.Typer()

# Construct cli from subfiles
app.command()(run.run)
app.command()(clean.clean)
app.command()(sync.sync)

info_app = typer.Typer()
info_app.add_typer(info.model_app, name='models')
info_app.add_typer(info.results_app, name='results')

app.add_typer(info_app, name='info')
#app.command()(setup.setup)
#app.command()(rollback.rollback)
#app.command()(install.install)

dvc_app = typer.Typer()
app.add_typer(dvc.app, name="dvc")

vis_app = typer.Typer()
app.add_typer(vis.app, name="vis")


@app.callback()
def global_state(ctx: typer.Context, verbose: bool = False, dry: bool = False):
    """
    This function will be run before every cli function
    It sets up the current state and sets global settings.
    """

    config = state.get_state(verbose, dry)

    config.console.print('Running in verbose mode')
    config.console.print('Running in dry mode')

    config.load_experiment_config()

    # Ensure that sdem is running in the correct folder etc
    #   This is not required if setup is being called and so we simply check that the command is not setup
    if not (ctx.invoked_subcommand in commands_no_start_up_check):
        pass_flag = config.check()

        if not pass_flag:
            exit()

    # store the config in the typer/click context that will be passed to all commands
    ctx.obj = config


def main():
    app()
