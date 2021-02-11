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

_DEFAULT_TEMPLATE = {
    'run_dir': '.',
    'experiment_prefix': None,
    'model_dir': 'models',
    'ignore_dirs': ['models/checkpoints'],
    'scared_run_files': 'models/runs',
    'results_files': 'results',
    'data_files': 'data',
    'run_command': 'python ',
    'delete_dir': None, #this will permanently delete files
    'tmp_dir': 'tmp',
    'bin_dir': 'bin_model_log',
    'local_config': 'experiment_config.yaml',
    'project_config': '../project_config.yaml',
    'global_config': None,
    'result_name_fn': lambda config: '{name}_{_id}'.format(name=config['name'], _id=config['experiment_id']),
    'results_metric_fn': lambda results: results['metrics'], 
    'use_mongo': False
}

@dispatch.register('template', '')
def default_template():
    return _DEFAULT_TEMPLATE

def check_template(template):
    for key in REQUIRED_KEYS:
        if key not in template.keys():
            raise RuntimeError(f'Template requires key: {key}')


def get_template():
    tmpl = dispatch.dispatch('template', '')()
    check_template(tmpl)
    return tmpl

