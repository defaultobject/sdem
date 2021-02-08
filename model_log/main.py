import typer
from loguru import logger

from . import state #global settings
from . import template

from .computation import startup

from .cli import run 
from .cli import dvc 
from .cli import clean 
from .cli import vis 
from .cli import sync 


app = typer.Typer()

#add run command directly to app
app.command()(run.run)
app.command()(clean.clean)
app.command()(sync.sync)

dvc_app = typer.Typer()
app.add_typer(dvc.app, name="dvc")

vis_app = typer.Typer()
app.add_typer(vis.app, name="vis")


@app.callback()
def global_state(verbose: bool = False, dry: bool = False):
    if verbose:
        #logger.info("Will write verbose output")
        state.verbose = True

    if dry:
        #logger.info("Will write verbose output")
        state.dry = True

    #Ensure that model_log is running in the correct folder etc
    pass_flag = startup.check()

    if not pass_flag:
        exit()

    #load config
    config = startup.load_config()
    state.experiment_config = config

def main():
    app()
