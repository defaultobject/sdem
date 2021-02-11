import os
from pathlib import Path


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

def get_docker_run_command(run_config):
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

