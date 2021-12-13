import os
from pathlib import Path

from . import manager
from .. import utils


def get_mount_str(d, mount_target=None, read_only=True):

    # Normalise target so that it ends with a backslash
    mount_target = utils.ensure_backslash(mount_target)

    if read_only:
        mount_str = " -v {d}:" + mount_target +"{t} "
    else:
        mount_str = ' --mount src="{d}",target='+mount_target+'{t},type=bind '

    if type(d) is list:
        # target mount point has been explictely passed thorugh
        _d = d[0]
        _t = d[1]
    else:
        _d = d
        _t = d

    # expand home directory
    if _d.startswith("~"):
        home = str(Path.home())
        _d = home + _d[1:]

    # get absolute path of directory.file
    d_path = os.path.abspath(_d)

    # get last folder/ as mount point
    t_path = os.path.basename(os.path.normpath(_t))

    s = mount_str.format(d=d_path, t=t_path)
    return s


def get_docker_run_command(experiment_config, run_config):
    """ Return the command used to run docker with required files mounted. """

    # Docker image name
    docker_name = run_config["name"]

    # By default we mount the results folder (if exists) and the models folder 
    dirs = [
        str(manager.get_models_folder_path(experiment_config)),
        str(manager.get_results_path(experiment_config))
    ]

    # Append the configs to be mounted
    libs = run_config["libs"] + [
        experiment_config['experiment_configs']['local'],
        experiment_config['experiment_configs']['project']
    ]

    flags = ' '.join(run_config['flags'])
    mount_target = run_config['mount_target']

    # Docker mount strings look like:
    #   Read only:
    #     -v {d}:/home/app/{t}
    #   Read/Write
    #     --mount src="{d}",target=/home/app/{t},type=bind 
    total_mount_str = ""
    for d in dirs:
        total_mount_str += get_mount_str(d, mount_target=mount_target, read_only=False)

    for d in libs:
        total_mount_str += get_mount_str(d, mount_target=mount_target, read_only=True)

    run_command = "docker  run  {mount_str} {flags} {name}".format(
        name=docker_name,
        flags=flags,
        mount_str=total_mount_str
    )
    return run_command
