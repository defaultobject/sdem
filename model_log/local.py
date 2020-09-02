from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import os
import seml.queuing
import signal

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess

import hashlib

from . import settings

def run_experiments(experiments, experiment_config, run_config):
    """
        Runs all experiments in experiments sequentially on the local machine
        These experiments will be run using a file storage observed which will be converted 
            to a mongo entry after running.
    """
    try:
        for exp in experiments:
            name = exp['filename']
            order_id = exp['order_id']

            if settings.verbose_flag:
                print('Running experiment {name} {order}'.format(name=name, order=order_id))

            #run experiment
            code = os.system('cd models; python {name} {order}'.format(name=name, order=order_id))
            print(code)

            if code == signal.SIGINT:
                print('Finishing all runs early!')
                break

            if settings.verbose_flag:
                print('Finished experiment {name} {order}'.format(name=name, order=order_id))

    except KeyboardInterrupt:
        print('Finishing all runs early!')
        pass






