from loguru import logger

from .. import state
from .. import decorators
from ..utils import ask_permission
from .. import template

from . import manager, sacred_manager, cluster

import os


def clean(experiment_config):
    """
    We do not delete any experiments, only move them to a temporal folder.
    """

    bin_path = manager.make_and_get_tmp_delete_folder(experiment_config)

    use_mongo = False

    if experiment_config['template']["use_mongo"]:
        raise NotImplementedError()

    ask_permission(
        "Prune experiment files?", lambda: sacred_manager.prune_experiments(bin_path, experiment_config)
    )

    ask_permission("Fix Run IDs?", lambda: sacred_manager.fix_filestorage_ids(experiment_config))

    ask_permission("Prune results files?", lambda: sacred_manager.prune_results(bin_path, experiment_config))

    if use_mongo:
        ask_permission("Re-sync local files with mongo?", lambda: None)

        ask_permission("Remove untracked mongo files?", lambda: None)

        ask_permission("Remove untracked artifact files?", lambda: None)

    ask_permission("Remove tempory folder?", lambda: manager.remove_tmp_folder(bin_path, experiment_config))

    # If nothing has been deleted then delete the bin_path
    manager.remove_bin_folder_if_empty(bin_path)
