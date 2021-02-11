from . import state

def run_if_not_dry(func):

    def inner(*args, **kwargs):
        if state.dry:
            return None
        else:
            return func(*args, **kwargs)

    return inner
