"""
    Describes the experiment layout w.r.t to the root experiment directory
"""

from . import dispatch

@dispatch.register('template', '')
def default_template():
    return {
        'model_files': 'models',
        'scared_run_files': 'models/runs',
        'results_files': 'results',
        'data_files': 'data',
        'delete_dir': None, #this will permanently delete files
        'tmp_dir': 'tmp' 
    }
