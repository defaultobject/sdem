from loguru import logger

from .. import state
from .. import decorators
from ..utils import ask_permission

@decorators.run_if_not_dry
def clean():
    if state.use_mongo:
        ask_permission(
            'Sync local files with mongo?',
            lambda: None
        )

    ask_permission(
        'Prune experiment files and fix IDs?',
        lambda: None
    )

    if state.use_mongo:
        ask_permission(
            'Re-sync local files with mongo?',
            lambda: None
        )

    ask_permission(
        'Remove untracked mongo files?',
        lambda: None
    )


    ask_permission(
        'Remove untracked artifact files?',
        lambda: None
    )

    ask_permission(
        'Remove cluster temp files?',
        lambda: None
    )
