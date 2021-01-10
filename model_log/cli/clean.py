import typer

from .. import config
from .. import dispatch

def clean(
    location: str = typer.Option("local", help=config.help_texts['location']),
):
    pass


