verbose = False
dry = False

help_texts = {
    "location": "Location to run code e.g docker/local",
    "force_all": "Force all experiment to re run, otherwise will only run those that have not already completed",
    "filter": "",
    "filter_file": "",
    "observer": "Run experiment with a sacred observer",
}

experiment_config = {
    'experiment_configs': {
        'local': 'experiment_config.yaml',
        'project': '../sdem_project_config.yaml',
    },
    'template': {
        'experiment_file' : 'm_*.py',
        'run_command': {
            'docker': 'cd models; python {name} {order}',
            'local': 'cd models; python {name} {order}',
            'local_no_observer': 'cd models; python {name} {order} --no-observer',
        },
        'folder_structure': {
            'model_files': 'models',
            'scared_run_files': 'models/runs',
            'bin': 'models/runs',
            'tmp': 'tmp'
        }
    }
}
