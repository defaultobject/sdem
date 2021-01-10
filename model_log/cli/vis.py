import typer

from .. import config

app = typer.Typer()

@app.command('omniboard')
def omniboard():
    print(f'omniboard')




