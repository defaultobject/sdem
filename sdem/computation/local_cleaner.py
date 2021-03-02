from loguru import logger

from .. import state
from .. import decorators
from ..utils import ask_permission
from .. import template

from . import manager, sacred_manager, cluster

import os


@decorators.run_if_not_dry
def clean():
    """
    We do not delete any experiments, only move them to a temporal folder.
    """

    tmpl = template.get_template()

    tmp_id = manager.make_and_get_tmp_delete_folder()

    if tmpl["use_mongo"]:
        ask_permission("Sync local files with mongo?", lambda: None)

    ask_permission(
        "Prune experiment files?", lambda: sacred_manager.prune_experiments(tmp_id)
    )

    ask_permission("Fix Run IDs?", lambda: sacred_manager.fix_filestorage_ids())

    ask_permission("Prune results files?", lambda: sacred_manager.prune_results(tmp_id))

    if tmpl["use_mongo"]:
        ask_permission("Re-sync local files with mongo?", lambda: None)

        ask_permission("Remove untracked mongo files?", lambda: None)

        ask_permission("Remove untracked artifact files?", lambda: None)

    ask_permission("Remove cluster temp files?", lambda: cluster.clean_up_temp_files())

    manager.remove_tmp_folder_if_empty(tmp_id)
