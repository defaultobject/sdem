from loguru import logger

from .. import decorators
from ..utils import ask_permission
from .. import template

from . import manager, sacred_manager, cluster

import os


def clean(state, delete_all):
    """
    We do not delete any experiments, only move them to a temporal folder.
    """

    experiment_config = state.experiment_config
    bin_path = manager.make_and_get_tmp_delete_folder(experiment_config)

    use_mongo = False

    if experiment_config['template']["use_mongo"]:
        raise NotImplementedError()

    if delete_all:
        ask_permission(
            "Delete ALL files?", lambda: sacred_manager.delete_all_experiments(state, bin_path, experiment_config)
        )
    else:
        ask_permission(
            "Prune experiment files?", lambda: sacred_manager.prune_experiments(state, bin_path, experiment_config)
        )

    ask_permission("Fix Run IDs?", lambda: sacred_manager.fix_filestorage_ids(state, experiment_config))

    ask_permission("Prune results files?", lambda: sacred_manager.prune_results(state, bin_path, experiment_config))

    if use_mongo:
        ask_permission("Re-sync local files with mongo?", lambda: None)

        ask_permission("Remove untracked mongo files?", lambda: None)

        ask_permission("Remove untracked artifact files?", lambda: None)

    ask_permission("Remove tempory folder?", lambda: manager.remove_tmp_folder(bin_path, experiment_config))

    # If nothing has been deleted then delete the bin_path
    manager.remove_bin_folder_if_empty(bin_path)
