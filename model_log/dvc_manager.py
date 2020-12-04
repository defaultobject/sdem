import os
def save_to_storage():
    script = """
        dvc add results
        dvc add models/runs
        git add results.dvc
        git add models/runs.dvc
        git commit -m 'dvc push'
        dvc push
    """
    os.system(script)
    print('REMEMBER TO GIT PUSH!')

def get_from_storage():
    script = """
        dvc pull results.dvc
        dvc pull models/runs.dvc
    """
    os.system(script)

def sync_with_dvc():
    pass
