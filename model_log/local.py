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

from pathlib import Path

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess

import hashlib

from . import settings

def run_file(experiment_config, run_config):
    if ('docker' in run_config.keys()) and (run_config['docker']):
        code = run_file_docker(experiment_config, run_config)
    else:
        run_command =  'python {name}'
        code = os.system(run_command.format(name=experiment_config['run_file']))

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

            print(run_config.keys())
            if ('docker' in run_config.keys()) and (run_config['docker']):
                print('runnning in docker')
                code = run_docker(exp, experiment_config, run_config)
            else:
                print('runnning locally')

                observer = '1'

                if experiment_config['no_observer']:
                    observer = '0'

                run_command =  'cd models; python {name} {order} {observer}'
                code = os.system(run_command.format(name=name, order=order_id, observer=observer))

            if code == signal.SIGINT:
                print('Finishing all runs early!')
                break

            if settings.verbose_flag:
                print('Finished experiment {name} {order}'.format(name=name, order=order_id))

    except KeyboardInterrupt:
        print('Finishing all runs early!')
        pass

def ensure_backslash(s):
    if s[-1] != '/':
        return s + '/'
    return s

def get_mount_str(d, read_only=True):
    if read_only:
        mount_str = ' -v {d}:/home/app/{t} '
    else:
        mount_str = ' --mount src="{d}",target=/home/app/{t},type=bind '

    if type(d) is list:
        #target mount point has been explictely passed thorugh
        _d = d[0]
        _t = d[1]
    else:
        _d = d
        _t = d

    #expand home directory
    if _d.startswith('~'):
        home = str(Path.home())
        _d = home + _d[1:]

    #get absolute path of directory.file
    d_path = os.path.abspath(_d)

    #get last folder/ as mount point

    t_path = os.path.basename(os.path.normpath(_t))

    s = mount_str.format(d=d_path, t=t_path)
    return s

def get_docker_run_command(experiment_config, run_config):
    docker_name = run_config['name']

    #mount relavant dirs

    #will be binded
    dirs = ['models', 'results']

    #will be read only
    libs = run_config['libs'] + ['experiment_config.yaml']

    total_mount_str = ''
    for d in dirs:
        total_mount_str += get_mount_str(d, read_only=False)

    for d in libs:
        total_mount_str += get_mount_str(d, read_only=True)


    run_command =  'docker  run  {mount_str} {name}'.format(
        name=docker_name,
        mount_str=total_mount_str
    )
    return run_command


def run_docker(exp, experiment_config, run_config):
    name = exp['filename']
    order_id = exp['order_id']

    run_command = get_docker_run_command(experiment_config, run_config)

    observer = '1'

    if experiment_config['no_observer']:
        observer = '0'

    run_exp_command =  ' /bin/bash -c  "cd /home/app/models; python {name} {order} {observer}"'.format(name=name, order=order_id, observer=observer)

    run_command += run_exp_command

    if settings.verbose_flag:
        print(run_command)

    code = os.system(run_command)
    return code



def run_file_docker(experiment_config, run_config):
    run_config['libs'].append(experiment_config['run_file'])

    run_command = get_docker_run_command(experiment_config, run_config)


    run_exp_command =  ' /bin/bash -c  "cd /home/app; python {name} "'.format(name=experiment_config['run_file'])

    run_command += run_exp_command

    if settings.verbose_flag:
        print(run_command)

    code = os.system(run_command)
    return code




