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
        'use_mongo': False,
        'experiment_file' : 'm_*.py',
        'run_command': {
            'docker': 'cd /home/app; cd models; python {filename} {order_id}',
            'docker_no_observer': 'cd /home/app; cd models; python {filename} {order_id} --no-observer',
            'local': 'cd models; python {filename} {order_id}',
            'local_no_observer': 'cd models; python {filename} {order_id} --no-observer',
            'cluster': 'python {filename} {order_id}',
        },
        'folder_structure': {
            'model_files': 'models',
            'scared_run_files': 'models/runs',
            'bin': 'sdem_bin',
            'tmp': 'tmp',
            'results': {
                'root': 'results',
                'file': '{name}_{experiment_id}.pickle'
            }
        }
    }
}
