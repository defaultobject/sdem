from loguru import logger

from .. import state
from .. import decorators
from .. import template
from .. import utils
from . import manager

import os

import slurmjobs
from slurmjobs.args import NoArgVal
import slurmjobs.util as util

import shutil
import zipfile
import subprocess


UNPACK_ON_CLUSTER_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
unzip cluster.zip -d {exp_name}
rm -rf cluster.zip
cd {exp_name}
mkdir results
{jobs}
HERE"""

SSH_SCRIPT = """ssh  -i {key} "{remotehost}" -o StrictHostKeyChecking=no 'bash -s' << HERE
cd {exp_name}
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

SYNC_SCRIPT = 'cd ../ && rsync -ra --relative --progress --compress -e "ssh -i {key}" {remotehost}:{folder_dest} {folder_origin}'
LOCAL_SYNC_SCRIPT = (
    "mkdir -p {folder_origin} && rsync -ra {folder_dest} {folder_origin}"
)

CLUSTER_ZIP = "jobs/cluster.zip"

FOLDERS_TO_SYNC = ["jobs/", "results/", "models/runs/_sources"]


def check_if_experiment_exists_on_cluster(exp_name, cluster_config):
    """
    Return true if a folder exp_name exists in the home directory of the cluster
        otherwise return false
    """
    remotehost = "{user}@{host}".format(
        user=cluster_config["user"], host=cluster_config["host"]
    )
    script = CHECK_IF_EXPERIMENT_ON_CLUSTER_SCRIPT.format(
        key=cluster_config["key"], remotehost=remotehost, exp_name=exp_name
    )
    try:
        cout = subprocess.run(script, stdout=subprocess.PIPE, shell=True).stdout.decode(
            "utf-8"
        )
        if int(cout) == 1:
            return True
    except Exception as e:
        print(e)
        print("continuing and assuming experiment does not exist")

    return False


def create_slurm_scripts(configs_to_run, run_settings, experiment_name, cluster_config):
    """
    Creates slurm scripts by:
        Creates a unique folder in jobs for every file in configs_to_run

        If a sif file is defined in the configs_to_run this is used
        If a sif file is defined in the cluster config, this is used
        Otherwise no sif file is used

    NOTE: scripts have to been run like 
        python {filename}.py {order_id}
    """

    class ValueArgument(slurmjobs.args.FireArgument):
        kw_fmt = "{value}"

        @classmethod
        def format_value(cls, v):
            return v

        @classmethod
        def format_arg(cls, k, v=NoArgVal):
            if v is NoArgVal:
                return cls.format_value(k)
            return cls.kw_fmt.format(key=k, value=cls.format_value(v))

    # distinct file names
    files_to_run = list(set([c["filename"] for c in configs_to_run]))
    for _file in files_to_run:
        configs_of_file = [c for c in configs_to_run if c["filename"] == _file]

        # assume that every config has the same sif file
        if "sif" in configs_of_file[0].keys():
            # run using singularity defined in model file
            run_command = "singularity run {sif_location}".format(
                sif_location=configs_of_file[0]["sif"]
            )
            run_command = run_command + " python {filename}"

        elif "sif" in cluster_config.keys():
            # run using singularity
            run_command = "singularity run {sif_location}".format(
                sif_location=cluster_config["sif"]
            )
            run_command = run_command + " python {filename}"
        else:
            run_command = "python {filename}"

        ncpus = 1  # this is actually the number of nodes
        ngpus = 0

        if "cpus" in cluster_config["sbatch"].keys():
            ncpus = cluster_config["sbatch"]["cpus"]
            cluster_config["sbatch"].pop("cpus")

        if "gpus" in cluster_config["sbatch"].keys():
            ngpus = cluster_config["sbatch"]["gpus"]
            cluster_config["sbatch"].pop("gpus")

        batch = slurmjobs.SlurmBatch(
            run_command.format(filename=_file),
            name=slurmjobs.util.command_to_name(
                "python {filename}".format(filename=_file)
            ),
            conda_env=None,
            cli="value",
            job_id=False,
            run_dir="~/{name}/models/".format(name=experiment_name),
            modules=cluster_config["modules"],
            sbatch_options=cluster_config["sbatch"],
            ncpus=ncpus,
            n_cpus=ncpus,  # get around a bug in slurm jobs
            ngpus=ngpus,
            n_gpus=ngpus,
        )

        # go over every order_id
        all_order_ids = [c["order_id"] for c in configs_of_file]
        run_script, job_paths = batch.generate([("order_id", all_order_ids)])


def compress_files_for_cluster(
    configs_to_run, run_settings, experiment_name, cluster_config
):
    tmpl = template.get_template()

    cluster_zip = CLUSTER_ZIP
    libs = cluster_config["libs"]
    files_to_move = (
        ["jobs/", "data/"]
        + libs
        + [tmpl["local_config"], tmpl["project_config"], tmpl["global_config"]]
    )
    folders_to_ignore = ["models/runs"] + tmpl["ignore_dirs"]

    # clean up existing runs of this functin
    if os.path.exists(cluster_zip):
        os.remove(cluster_zip)

    # go through every file to move and zip
    zipf = zipfile.ZipFile(cluster_zip, "w", zipfile.ZIP_DEFLATED)
    for f in files_to_move:
        if f is None:
            continue

        if type(f) == list:
            # this defines a file/folder with a target folder structure
            f_to_zip = f[0]
            f_target = f[1]

            if os.path.isdir(f_to_zip):
                utils.zip_dir(f_to_zip, zipf, dir_path=f_target)
            else:
                zipf.write(f_to_zip, f_target)

        elif os.path.exists(f):
            if os.path.isdir(f):
                utils.zip_dir(f, zipf)
            else:
                zipf.write(f)
        else:
            if state.verbose:
                logger.info("file {f} does not exists -- skipping!".format(f=f))

    # move models over. This is special case because we want to ignore the 'runs' folder.
    folder_to_move = "models/"
    utils.zip_dir(folder_to_move, zipf, ignore_dir_arr=folders_to_ignore)

    zipf.close()


def move_files_to_cluster(
    configs_to_run, run_settings, experiment_name, cluster_config
):

    # move zip file to cluster
    localfile = CLUSTER_ZIP
    remotehost = "{user}@{host}".format(
        user=cluster_config["user"], host=cluster_config["host"]
    )
    remotefile = "."

    if state.verbose:
        logger.info("sending files to: {remotehost}".format(remotehost=remotehost))

    s = 'scp -i %s "%s" "%s:%s"' % (
        cluster_config["key"],
        localfile,
        remotehost,
        remotefile,
    )

    os.system(s)

    # unzip on cluster

    files_to_run = list(set([c["filename"] for c in configs_to_run]))
    jobs = ""
    for _file in files_to_run:
        _filename = os.path.splitext(os.path.basename(_file))[0]

        jobs += "mkdir jobs/{_file}/slurm \n".format(_file=_filename)

    run_ssh_script = UNPACK_ON_CLUSTER_SCRIPT.format(
        key=cluster_config["key"],
        remotehost=remotehost,
        exp_name=experiment_name,
        jobs=jobs,
    )
    os.system(run_ssh_script)


def run_on_cluster(configs_to_run, run_settings, experiment_name, cluster_config):
    remotehost = "{user}@{host}".format(
        user=cluster_config["user"], host=cluster_config["host"]
    )

    files_to_run = list(set([c["filename"] for c in configs_to_run]))

    jobs = ""

    for _file in files_to_run:
        _filename = os.path.splitext(os.path.basename(_file))[0]

        jobs += "sh ./jobs/{_file}/run_{_file}.sh \n".format(_file=_filename)

    # run experiments and get batch ids
    run_ssh_script = SSH_SCRIPT.format(
        key=cluster_config["key"],
        remotehost=remotehost,
        exp_name=experiment_name,
        jobs=jobs,
    )

    os.system(run_ssh_script)


def cluster_run(configs_to_run, experiment_config, run_settings, location):
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
    cluster_config = experiment_config[location]
    experiment_name = manager.get_experiment_name(experiment_config)

    # Only run if the experiment is already on the cluster
    if check_if_experiment_exists_on_cluster(experiment_name, cluster_config):
        if state.verbose:
            logger.info(f"Experiment is already on cluster - {location}, exiting!")

        return None


    # Create HPC slurm scripts using slurmjobs
    create_slurm_scripts(configs_to_run, run_settings, experiment_name, cluster_config)

    # Zip all files to move to the cluster
    compress_files_for_cluster(
        configs_to_run, run_settings, experiment_name, cluster_config
    )

    # Move zip to the cluster and unwrap
    move_files_to_cluster(configs_to_run, run_settings, experiment_name, cluster_config)

    # Only run experiments on cluster if run_sbatch flag is true
    if run_settings["run_sbatch"]:
        run_on_cluster(configs_to_run, run_settings, experiment_name, cluster_config)


def clean_up_cluster(location, experiment_config):
    cluster_config = experiment_config[location]
    experiment_name = manager.get_experiment_name()

    if not (check_if_experiment_exists_on_cluster(experiment_name, cluster_config)):
        if state.verbose:
            logger.info(
                f"Experiment {experiment_name} is not on cluster - {location}, nothing to clean!"
            )

        return None

    ans = utils.ask_permission(f"Delete {experiment_name} on cluster?")

    # we do not have permission to delete the experiment
    if ans is False:
        return

    remotehost = "{user}@{host}".format(
        user=cluster_config["user"], host=cluster_config["host"]
    )
    script = CLEAN_UP_CLUSTER_SCRIPT.format(
        key=cluster_config["key"], remotehost=remotehost, exp_name=experiment_name
    )

    if state.verbose:
        logger.info(f"Cleaning {remotehost}")

    try:
        os.system(script)
    except Exception as e:
        if state.verbose:
            print(f"An error occured while cleaning - {remotehost}")

        print(e)


def sync_files(folders_to_sync, folder_origin, cluster_config):
    remotehost = "{user}@{host}".format(
        user=cluster_config["user"], host=cluster_config["host"]
    )

    sync_script_f = SYNC_SCRIPT.format(
        key=cluster_config["key"],
        remotehost=remotehost,
        folder_dest=folders_to_sync,
        folder_origin=folder_origin,
    )
    os.system(sync_script_f)


def local_sync(folder_origin):
    # sync files from cluster_tmp to experiment folders
    folders_to_sync = FOLDERS_TO_SYNC

    for folder in folders_to_sync:
        _origin = folder_origin + folder
        _dest = folder
        if state.verbose:
            print(f"local sync: {_origin} -> {_dest}")

        _script = LOCAL_SYNC_SCRIPT.format(folder_dest=_origin, folder_origin=_dest)
        os.system(_script)


def get_folders_to_sync(experiment_name, cluster_config):
    # this does not sync models because that is delt with separetly so that the sacred ids can be fixed

    folders_to_sync = FOLDERS_TO_SYNC

    # get list of folders that we need to sync from cluster

    if "sync" in cluster_config.keys():
        folders_to_sync += cluster_config["sync"]

    if "sync_folders" in cluster_config.keys():
        folders_to_sync += cluster_config["sync_folders"]

    folders_to_sync = [experiment_name + "/" + f for f in folders_to_sync]
    folders_to_sync = "'" + " ".join(folders_to_sync) + "'"

    return folders_to_sync


def fix_run_ids(experiment_name):
    """
    Sacred runs start from 1. To merge cluster runs and local runs we simply
        get the max run id locally, rename all cluster runs to add on the max id and
        then merge

    This guarrentees that there will be no conflicts, and assuming no runs have been deleted
        will ensure that the runs are named sequentially
    """
    # if there are any sacred experiments they will be in cluster_temp/experiment_name/models/runs/*
    runs_root = "models/runs/"
    remote_root = "cluster_temp/" + experiment_name + "/models/runs/"

    if not (os.path.exists(remote_root)):
        # it seems nothing was synced and so cluster_temp does not exist
        if state.verbose:
            logger.info("No sacred runs were synced, so no run ids to fix, continuing")
        return

    utils.mkdir_if_not_exists(runs_root)

    # get max id
    origin_ids = [int(folder) for folder in os.listdir(runs_root) if folder.isnumeric()]
    max_id = 1
    if len(origin_ids) > 0:
        max_id = max(origin_ids) + 1

    remote_files = [folder for folder in os.listdir(remote_root) if folder.isnumeric()]

    for i, _file in enumerate(remote_files):
        filepath = remote_root + _file
        _id = max_id + i
        os.system("mv {filepath} models/runs/{_id}".format(filepath=filepath, _id=_id))


@decorators.run_if_not_dry
def sync_with_cluster(location):
    """
    We sync from the cluster to cluster_temp and then locally sync from cluster_temp to the experiment folders.
    This is to get around the fact the experiment folder on the cluster may be prefixed.
    """
    experiment_config = state.experiment_config
    cluster_config = experiment_config[location]
    experiment_name = manager.get_experiment_name()
    experiment_folder_name = manager.get_experiment_folder_name()

    if not (check_if_experiment_exists_on_cluster(experiment_name, cluster_config)):
        if state.verbose:
            logger.info(f"No experiment to sync on cluster - {location}, exiting!")

        return None

    # get folders to sync without models folder
    # on the cluster the folder created may be prefixed, so we need the folder names
    # on the cluster and locally may not match up. hence sync to the local experiment
    # folder name
    folders_to_sync = get_folders_to_sync(experiment_name, cluster_config)

    # move files from cluster into cluster_temp
    sync_files(
        folders_to_sync, experiment_folder_name + "/cluster_temp/", cluster_config
    )
    local_sync("cluster_temp/" + experiment_name + "/")

    folder_origin = experiment_folder_name + "/cluster_temp/"
    sync_files(experiment_name + "/models/", folder_origin, cluster_config)

    # fix sacred run ids
    fix_run_ids(experiment_name)

    # clean up
    os.system("rm -rf cluster_temp")


def clean_up_temp_files():
    tmpl = template.get_template()

    utils.remove_dir_if_exists("jobs")
    utils.remove_dir_if_exists("cluster_temp")
