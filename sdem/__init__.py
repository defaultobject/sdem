from pkg_resources import get_distribution
from .experiment import Experiment

__all__ = ['Experiment']
__version__ = get_distribution('sdem').version
