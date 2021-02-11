import typer

from .. import state
from ..computation.sacred_vis import start_omniboard
from ..computation import sacred_manager

app = typer.Typer()

@app.command('omniboard')
def omniboard():
    exp_name = sacred_manager.get_experiment_name()

    start_omniboard(exp_name)




