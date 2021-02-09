from loguru import logger

from .. import state
from .. import decorators
from . import manager

import os

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess


SSH_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
unzip cluster.zip -d {exp_name}
rm -rf cluster.zip
cd {exp_name}
mkdir results
{jobs}
HERE"""

CHECK_IF_EXPERIMENT_ON_CLUSTER_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
    test -d "{exp_name}" && echo "1" || echo "0"
HERE"""


CLEAN_UP_CLUSTER_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
rm -rf cluster.zip
rm -rf {exp_name}
HERE"""

CHECK_CLUSTER_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
    squeue -u {user}
HERE"""

def check_if_experiment_exists_on_cluster(exp_name, cluster_config):
    remotehost = '{user}@{host}'.format(user=cluster_config['user'], host=cluster_config['host'])
    script = CHECK_IF_EXPERIMENT_ON_CLUSTER_SCRIPT.format(key=cluster_config['key'], remotehost=remotehost, exp_name=exp_name)
    try:    
        cout = subprocess.run(script, stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
        if int(cout) == 1:
            return True
    except Exception as e:
        print(e)
        print('continuing and assuming experiment does not exist')

    return False

def create_slurm_scripts(configs_to_run, run_settings, experiment_name, cluster_config):
    """
        Creates slurm scripts by:
            Creates a unique folder in jobs for every file in configs_to_run

            If a sif file is defined in the configs_to_run this is used
            If a sif file is defined in the cluster config, this is used
            Otherwise no sif file is used
    """

    class ValueArgument(slurmjobs.args.FireArgument):
        kw_fmt = '{value}'

        @classmethod
        def format_value(cls, v):
            return v

        @classmethod
        def format_arg(cls, k, v=NoArgVal):
            if v is NoArgVal:
                return cls.format_value(k)
            return cls.kw_fmt.format(key=k, value=cls.format_value(v))


    #distinct file names
    files_to_run = list(set([c['filename'] for c in configs_to_run]))
    for _file in files_to_run:
        configs_of_file = [c for c in configs_to_run if c['filename'] == _file]

        #assume that every config has the same sif file
        if 'sif' in configs_of_file[0].keys():
            #run using singularity defined in model file
            run_command = 'singularity run {sif_location}'.format(sif_location=configs_of_file[0]['sif'])
            run_command = run_command + ' python {filename}'

        elif 'sif' in cluster_config.keys():
            #run using singularity
            run_command = 'singularity run {sif_location}'.format(sif_location=cluster_config['sif'])
            run_command = run_command + ' python {filename}'
        else:
            run_command = 'python {filename}'

        ncpus=1 #this is actually the number of nodes
        ngpus=0

        if 'cpus' in cluster_config['sbatch'].keys():
            ncpus = cluster_config['sbatch']['cpus']
            cluster_config['sbatch'].pop('cpus')

        if 'gpus' in cluster_config['sbatch'].keys():
            ngpus = cluster_config['sbatch']['gpus']
            cluster_config['sbatch'].pop('gpus')

        batch = slurmjobs.SlurmBatch(
            run_command.format(filename=_file),
            name=slurmjobs.util.command_to_name('python {filename}'.format(filename=_file)),
            conda_env=None,
            cli = 'value',
            job_id=False,
            run_dir='~/{name}/models/'.format(name=experiment_name),
            modules=cluster_config['modules'],
            sbatch_options=cluster_config['sbatch'],
            ncpus=ncpus,
            n_cpus=ncpus, #get around a bug in slurm jobs
            ngpus=ngpus,
            n_gpus=ngpus,
        )

        #go over every order_id
        all_order_ids = [c['order_id'] for c in configs_of_file]
        run_script, job_paths = batch.generate([('order_id', all_order_ids)])   

def compress_files_for_cluster(configs_to_run, run_settings, experiment_name, cluster_config):
    pass

def move_files_to_cluster(configs_to_run, run_settings, experiment_name, cluster_config):
    pass

def run_on_cluster(configs_to_run, run_settings, experiment_name, cluster_config):
    """
        To run on cluster we:
            Create slurm scripts of running
            Compress files to send over to cluster
            Move files to cluster
            Run slurm scripts
    """




@decorators.run_if_not_dry
def cluster_run(configs_to_run, run_settings, location):
    """
        Checks if experiment is not already on cluster
            if so then exit
            else setup on cluster and run

        To run on cluster we:
            Create slurm scripts of running
            Compress files to send over to cluster
            Move files to cluster
            Run slurm scripts
    """
    experiment_config = state.experiment_config
    cluster_config = experiment_config[location]
    experiment_name = manager.get_experiment_name()

    if check_if_experiment_exists_on_cluster(experiment_name, cluster_config):
        if state.verbose:
            logger.info(f'Experiment is already on cluster - {location}, exiting!')

        return None

    create_slurm_scripts(configs_to_run, run_settings, experiment_name, cluster_config)
    compress_files_for_cluster(configs_to_run, run_settings, experiment_name, cluster_config)
    move_files_to_cluster(configs_to_run, run_settings, experiment_name, cluster_config)
    run_on_cluster(configs_to_run, run_settings, experiment_name, cluster_config)
