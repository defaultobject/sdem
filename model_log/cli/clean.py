import typer

from .. import state
from .. import dispatch

def clean(
    location: str = typer.Option("local", help=state.help_texts['location']),
):
    pass


