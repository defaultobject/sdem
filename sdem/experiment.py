""" Wrapper around SacredExperiment. """
from sacred import Experiment as SacredExperiment
from sacred.observers import FileStorageObserver

import argparse
from pathlib import Path

import sys

from .computation import manager
from .computation import metrics

from .utils import pass_unknown_kargs

import inspect
import os


class Experiment(SacredExperiment):
    def __init__(self, name="exp"):
        caller_globals = inspect.stack()[1][0].f_globals
        # sacred used inspect.stack() to see where the main function has been called from.
        #   This is awkward when trying to call an experiment from a different class.
        #   To get around this we check if the the experiment has been run from the command line.
        #   If not then we change the working dir to the experiments directory.

        if caller_globals["__name__"] == "__main__":
            super(Experiment, self).__init__(name)
        else:
            prev_cwd = os.getcwd()
            os.chdir("../")
            super(Experiment, self).__init__(name)
            os.chdir(prev_cwd)

        self.config_function = None
        self.model_function = None
        self.predict_function = None

    def configs(self, function):
        self.config_function = function

    def run_config(self, function, config, use_observer=True, **kwargs):
        self.observers = []  # reset observed
        self.configurations = []

        if use_observer:
            self.observers.append(FileStorageObserver("runs"))

        self.add_config(config)
        captured_function = self.main(lambda: function(config, **kwargs))

        #call sacred run method
        self.run(captured_function.__name__)

    def log_scalar(self, name, metric):
        # only log when there is an observer
        if len(self.observers) > 0:
            super(Experiment, self).log_scalar(name, metric)

    def log_metrics(self, X, Y, prediction_fn, var_flag=True, log=True, prefix=None):
        return metrics.log_regression_scalar_metrics(
            self, X, Y, prediction_fn, var_flag=var_flag, log=log, prefix=prefix
        )

    def model(self, function):
        """ For returning the trained model.  """
        self.model_function = function

    def predict(self, function):
        """ For computing results.  """
        self.predict_function = function

    def automain(self, function):
        """
        automain, copies the functionality of sacred automain. Will run the experiment using a specific input

        when the file is run from command line we support the follow command line arguments:
            int>=0: run specific config id [default = 0]
            -1: run all experiment configs
        """

        # check if the function was run through the command line or imported
        # if imported we do not run the experiments

        # TODO: check if required
        # captured = self.main(function)
        if function.__module__ != "__main__":
            return

        if self.config_function is None:
            raise RuntimeError("No config function registered. ")

        filename = Path(inspect.getfile(function))

        parser = argparse.ArgumentParser()
        parser.add_argument('i', type=int, default=-1, help='Experiment id to run')
        parser.add_argument('--no-observer', action='store_true', default=False, help='Run without observer')
        input_args, unknown_args = parser.parse_known_args()

        unknown_kwargs = pass_unknown_kargs(unknown_args)

        use_observer = not(input_args.no_observer)
        i = input_args.i

        configs = self.config_function()

        if i == -1:
            # Run all experiments
            for i, config in enumerate(configs):
                config = manager.ensure_correct_fields_for_model_file_config(
                    filename, config, i
                )
                self.run_config(function, config, use_observer=use_observer, **unknown_kwargs)

        else:
            # Run specific experiment
            config = manager.ensure_correct_fields_for_model_file_config(
                filename, configs[i], i
            )
            self.run_config(function, config, use_observer=use_observer, **unknown_kwargs)
