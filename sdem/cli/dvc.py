import typer

from .. import state
from .. import template
from loguru import logger

app = typer.Typer()

import os

def save_to_storage():
    tmpl = template.get_template()

    results_root = tmpl['results_files']
    runs_root = tmpl['scared_run_files']
    model_dir = tmpl['model_dir']

    script = f"""
        dvc add {results_root}
        dvc add {runs_root}
        git add results.dvc
        git add {model_dir}/runs.dvc
        git commit -m 'dvc push'
        dvc push
    """
    os.system(script)

    logger.info('REMEMBER TO GIT PUSH!')

def get_from_storage():
    tmpl = template.get_template()
    model_dir = tmpl['model_dir']

    script = f"""
        dvc pull results.dvc
        dvc pull {model_dir}/runs.dvc
    """
    os.system(script)

@app.command('push')
def dvc_push():
    save_to_storage()

@app.command('pull')
def dvc_pull():
    get_from_storage()

