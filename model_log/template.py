"""
    Describes the experiment layout w.r.t to the root experiment directory
"""

from . import dispatch

REQUIRED_KEYS = [
    'run_dir',
    'experiment_prefix',
    'model_dir',
    'scared_run_files',
    'results_files',
    'data_files',
    'tmp_dir'
]

@dispatch.register('template', '')
def default_template():
    return {
        'run_dir': '.',
        'experiment_prefix': None,
        'model_dir': 'models',
        'scared_run_files': 'models/runs',
        'results_files': 'results',
        'data_files': 'data',
        'delete_dir': None, #this will permanently delete files
        'tmp_dir': 'tmp'
    }

def check_template(template):
    for key in REQUIRED_KEYS:
        if key not in template.keys():
            raise RuntimeError(f'Template requires key: {key}')


def get_template():
    tmpl = dispatch.dispatch('template', '')()
    check_template(tmpl)
    return tmpl

