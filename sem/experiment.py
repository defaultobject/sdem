from sacred import Experiment as SacredExperiment
from sacred.observers import FileStorageObserver, MongoObserver

import sys

#from . import manager
#from . import metrics

import inspect
import os

class Experiment(SacredExperiment):
    def __init__(self,name='exp'):
        caller_globals = inspect.stack()[1][0].f_globals
        # sacred used inspect.stack() to see where the main function has been called from. This is annoying when trying to call an experiment from a different class.
        # to get around this we check if the the experiment has been run from the command line. If not then we change the working dir to the experiments directory.
        if caller_globals['__name__'] == '__main__':
            super(Experiment, self).__init__(name)
        else:
            prev_cwd = os.getcwd()
            os.chdir('../')
            super(Experiment, self).__init__(name)
            os.chdir(prev_cwd)

        self.config_function = None

    def configs(self, function):
        self.config_function = function

    def run_config(self, function, config, use_observer=True):
        self.observers = [] #reset observed
        self.configurations = []

        if use_observer:
            self.observers.append(FileStorageObserver('runs'))

        self.add_config(config)
        captured_function = self.main(lambda: function(config))
        self.run(captured_function.__name__)

    def log_metrics(self, X, Y, prediction_fn, var_flag=True, log=True, prefix=None):
        return metrics.log_regression_scalar_metrics(self, X, Y, prediction_fn, var_flag=var_flag, log=log, prefix=prefix)

    def automain(self, function):
        """
        automain, copies the functionality of sacred automain. Will run the experiment using a specific input

        when the file is run from command line we support the follow command line arguments:
            int>=0: run specific config id [default = 0]
            -1: run all experiment configs

        """

        #check if the function was run through the command line or imported
        #if imported we do not run the experiments
        captured = self.main(function)
        if function.__module__ != "__main__":
            return

        if self.config_function is None:
            raise RuntimeError('No config function registered. ')

        filename = inspect.getfile(function)

        use_observer=True
        i = 0
        if len(sys.argv) == 2:
            i = int(sys.argv[1])

        if len(sys.argv) == 3:
            i = int(sys.argv[1])
            flag = int(sys.argv[2])

            use_observer = flag

        configs = self.config_function()

        if i == -1:
            for i, config in enumerate(configs):
                config = manager.ensure_correct_fields_for_model_file_config(filename, config, i)
                self.run_config(function, config, use_observer=use_observer)
                
        else:
            config = manager.ensure_correct_fields_for_model_file_config(filename, configs[i], i)
            self.run_config(function, config, use_observer=use_observer)

