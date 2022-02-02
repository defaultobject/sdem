from .computation import manager

from rich.console import Console
from pathlib import Path
from loguru import logger

help_texts = {
    "location": "Location to run code e.g docker/local",
    "force_all": "Force all experiment to re run, otherwise will only run those that have not already completed",
    "filter": "",
    "filter_file": "",
    "observer": "Run experiment with a sacred observer",
}

class State:
    def __init__(self, verbose=False, dry=False, root = None):
        self.verbose = verbose
        self.dry = dry

        self.root = root

        #TODO stop console print when in verbose mode
        self.console = Console()

        self.experiment_config = {
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

    def load_experiment_config(self):
        self.console.rule('Loading experiment config')

        self.experiment_config = manager.get_experiment_config(
            self,
            self.experiment_config,
            exp_root=self.root
        )

        self.console.print(self.experiment_config)

    def check(self):
        """
        Runs startup checks:
            - ensures model log has been run in correct folder
        """
        model_folder = Path(self.experiment_config['template']['folder_structure']['model_files'])

        if not (model_folder.is_dir()):
            logger.error(f"No models folder ({model_folder.resolve()}), not in correct folder -- Exiting!")
            return False

        return True


    def load_externals(self):
        raise NotImplementedError()
        if "external_file" in experiment_config.keys():
            utils.load_mod(".", experiment_config["external_file"])
                
def get_state(verbose, dry):
    return State(verbose=verbose, dry=dry)
