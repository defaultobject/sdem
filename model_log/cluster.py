from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import os
import seml.queuing

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess

import hashlib

from . import util

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
 


def create_slurm_scripts(configs_to_run, experiment_config, run_config):
    """
        Creates a unique folder in jobs for every file in configs_to_run
    """


    experiment_name = experiment_config['experiment_name']

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


    if 'sif' in run_config.keys():
        #run using singularity
        run_command = 'singularity run {sif_location}'.format(sif_location=run_config['sif'])
        run_command = run_command + ' python {filename}'
    else:
        run_command = 'python {filename}'


    #distinct file names
    files_to_run = list(set([c['filename'] for c in configs_to_run]))
    for _file in files_to_run:
        configs_of_file = [c for c in configs_to_run if c['filename'] == _file]

        batch = slurmjobs.SlurmBatch(
            run_command.format(filename=_file),
            name=slurmjobs.util.command_to_name('python {filename}'.format(filename=_file)),
            conda_env=None,
            cli = 'value',
            job_id=False,
            run_dir='~/{name}/models/'.format(name=experiment_name),
            modules=run_config['modules'],
            sbatch_options=run_config['sbatch']
        )

        #go over every order_id
        all_order_ids = [c['order_id'] for c in configs_of_file]
        run_script, job_paths = batch.generate([('order_id', all_order_ids)])   


def zip_dir(path, zipf, ignore_dir=None, dir_path=None):
    """
        Path can be something like ../../folder_1/folder_2/lib/*
        we strip all leading directory structure and zip only lib/*
    """
    #target_dir = os.path.basename(os.path.normpath(path))

    path_split = os.path.normpath(path).split(os.sep)

    if dir_path is None:
        dir_path=''

    for root, dirs, files in os.walk(path):
        for f in files:
            if ignore_dir is not None:
                #if the root starts with ignore dir then we do not want to zip it
                if str(root).startswith(ignore_dir):
                    continue

            #remove leading directory structure
            root_split = os.path.normpath(root).split(os.sep)
            if dir_path:
                target_dir = dir_path
            else:
                target_dir = os.path.join(*root_split[(len(path_split)-1):])

            #zipf.write(os.path.join(root, f))    
            #print(os.path.join(target_dir, os.path.join(root, f)))
            zipf.write(os.path.join(root, f), os.path.join(target_dir, f))    



def check_if_experiment_exists_on_cluster(exp_name, run_config):
    remotehost = '{user}@{host}'.format(user=run_config['user'], host=run_config['host'])
    script = CHECK_IF_EXPERIMENT_ON_CLUSTER_SCRIPT.format(key=run_config['key'], remotehost=remotehost, exp_name=exp_name)
    try:    
        cout = subprocess.run(script, stdout=subprocess.PIPE, shell=True).stdout.decode('utf-8')
        if int(cout) == 1:
            return True
    except Exception as e:
        print(e)
        print('continuing and assuming experiment does not exist')

    return False

def clean_up_cluster(experiment_config, run_config):
    exp_name = experiment_config['experiment_name']
    remotehost = '{user}@{host}'.format(user=run_config['user'], host=run_config['host'])
    script = CLEAN_UP_CLUSTER_SCRIPT.format(key=run_config['key'], remotehost=remotehost, exp_name=exp_name)
    try:    
        os.system(script)
    except Exception as e:
        print('An error occured while cleanint')
        print(e)

def clean_up_temp_files(experiment_config, run_config):
    util.remove_dir_if_exists('jobs')
    util.remove_dir_if_exists('cluster_temp')

def sync_with_cluster(experiment_config, run_config):
    exp_name = experiment_config['experiment_name']

    #sync models separately because we need to fix the sacred _id
    folders_to_sync = ['jobs/', 'results/', 'models/runs/_sources']

    if 'sync_folders' in run_config.keys():
        folders_to_sync += run_config['sync_folders']

    remotehost = '{user}@{host}'.format(user=run_config['user'], host=run_config['host'])

    sync_script = 'cd ../ && rsync -ra --relative --progress --compress -e "ssh -i {key}" {remotehost}:{folder_dest} {folder_origin}' 

    folders_to_sync = [exp_name+'/'+f for f in folders_to_sync]
    folders_to_sync = "'"+' '.join(folders_to_sync)+"'"


    #sync jobs and results
    folder_origin = '.'
    sync_script_f = sync_script.format(key=run_config['key'], remotehost=remotehost, folder_dest=folders_to_sync, folder_origin=folder_origin)
    os.system(sync_script_f)

    #sync models
    folder_origin = exp_name+'/cluster_temp/'
    sync_script_f = sync_script.format(key=run_config['key'], remotehost=remotehost, folder_dest=exp_name+'/models/', folder_origin=folder_origin)
    os.system(sync_script_f)

    #if there are any sacred experiments they will be in cluster_temp/experiment_name/models/runs/*
    #get max id
    runs_root = 'models/runs/'
    remote_root = 'cluster_temp/'+exp_name+'/models/runs/'

    util.mkdir_if_not_exists(runs_root)

    origin_ids = [int(folder) for folder in os.listdir(runs_root) if folder.isnumeric()]
    max_id = 1
    if len(origin_ids) > 0:
        max_id = max(origin_ids) +1

    remote_files = [folder for folder in os.listdir(remote_root) if folder.isnumeric()]

    for i, _file in enumerate(remote_files):
        filepath = remote_root+_file
        _id = max_id + i 
        os.system('mv {filepath} models/runs/{_id}'.format(filepath=filepath, _id=_id))

    os.system('rm -rf cluster_temp')


def run_experiments(experiments, experiment_config, run_config):
    experiment_name = experiment_config['experiment_name']

    if check_if_experiment_exists_on_cluster(experiment_name, run_config):
        print('experiment already on cluster, clean up and try again')
        return

    create_slurm_scripts(experiments, experiment_config, run_config)


    cluster_zip = 'jobs/cluster.zip'
    libs = run_config['libs']
    files_to_move = ['jobs/', 'data/'] + libs

    #compress files to send to cluster
    if os.path.exists(cluster_zip):
        os.remove(cluster_zip)

    zipf = zipfile.ZipFile(cluster_zip, 'w', zipfile.ZIP_DEFLATED)
    for f in files_to_move:
        if type(f) == list:
            #this defines a file/folder with a target folder structure
            f_to_zip = f[0]
            f_target = f[1]

            if os.path.isdir(f_to_zip):
                zip_dir(f_to_zip, zipf, dir_path=f_target)
            else:
                zipf.write(f_to_zip, f_target)


        elif os.path.exists(f):
            if os.path.isdir(f):
                zip_dir(f, zipf)
            else:
                zipf.write(f)
        else:
            print('file {f} does not exists -- skipping!'.format(f=f))

    #move models over. This is special case because we want to ignore the 'runs' folder.
    folder_to_move = 'models/'
    ignore_folder = 'models/runs'
    zip_dir(folder_to_move, zipf, ignore_dir=ignore_folder)

    zipf.close()

    #send files to send to cluster
    localfile = cluster_zip
    remotehost = '{user}@{host}'.format(user=run_config['user'], host=run_config['host'])
    remotefile = '.'

    print('sending files to: {remotehost}'.format(remotehost=remotehost))
    s = 'scp -i %s "%s" "%s:%s"' % (run_config['key'], localfile, remotehost, remotefile)
    print(s)
    os.system(s)

    #run jobs
    files_to_run = list(set([c['filename'] for c in experiments]))
    
    jobs = ""
    for _file in files_to_run:
        _filename = os.path.splitext(os.path.basename(_file))[0]

        jobs += "mkdir jobs/{_file}/slurm && sh jobs/{_file}/run_{_file}.sh \n".format(_file=_filename)

    #run experiments and get batch ids
    run_ssh_script = SSH_SCRIPT.format(key=run_config['key'], remotehost=remotehost, exp_name=experiment_name, jobs=jobs)
    os.system(run_ssh_script)

def check_experiments(experiment_config, run_config):
    exp_name = experiment_config['experiment_name']
    remotehost = '{user}@{host}'.format(user=run_config['user'], host=run_config['host'])
    script = CHECK_CLUSTER_SCRIPT.format(key=run_config['key'], remotehost=remotehost, exp_name=exp_name, user=run_config['user'])
    try:    
        os.system(script)
    except Exception as e:
        print('An error occured while cleanint')
        print(e)
