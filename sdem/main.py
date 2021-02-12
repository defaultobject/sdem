import typer
from loguru import logger

from . import state #global settings
from . import template

from .computation import startup

from .cli import run, dvc, clean, vis, sync, setup, rollback, install

commands_no_start_up_check = ['setup', 'install']

app = typer.Typer()

#add run command directly to app
app.command()(run.run)
app.command()(clean.clean)
app.command()(sync.sync)
app.command()(setup.setup)
app.command()(rollback.rollback)
app.command()(install.install)

dvc_app = typer.Typer()
app.add_typer(dvc.app, name="dvc")

vis_app = typer.Typer()
app.add_typer(vis.app, name="vis")

@app.callback()
def global_state(ctx: typer.Context, verbose: bool = False, dry: bool = False):
    if verbose:
        #logger.info("Will write verbose output")
        state.verbose = True

    if dry:
        #logger.info("Will write verbose output")
        state.dry = True


    #Ensure that model_log is running in the correct folder etc
    #   This is not required if setup is being called and so we simply check that the command is not setup
    if not(ctx.invoked_subcommand in commands_no_start_up_check) :
        pass_flag = startup.check()

        if not pass_flag:
            exit()

    #load config
    config = startup.load_config()
    state.experiment_config = config

    #load any external files specified in the experiment_config
    startup.load_externals()


def main():
    app()
