import typer

from .. import config

app = typer.Typer()

@app.command('push')
def dvc_push():
    print(f'dvc_push')

@app.command('pull')
def dvc_pull():
    print(f'dvc_pull')
