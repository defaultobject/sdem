from loguru import logger
import sys

_REGISTERED = {}
 

#Register decorator
def register(group, key):
    """
        matches functions based on group and key
    """

    if group not in _REGISTERED:
        _REGISTERED[group] = {}


    def decorator(fun):
        _REGISTERED[group][key] = fun

        return fun

    return decorator

def dispatch(group, key):

    #oneerror: stops repeated eror being printed to terminal
    @logger.catch(reraise=True, onerror=lambda _: sys.exit(1))
    def find():
        return _REGISTERED[group][key]

    return find()
