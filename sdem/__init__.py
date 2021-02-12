from pkg_resources import get_distribution, DistributionNotFound
import os
from .experiment import Experiment

__all__ = ['Experiment']

#support pip installing and simplying adding to path
try:
    _dist = get_distribution('sdem')
    # Normalize case for Windows systems
    dist_loc = os.path.normcase(_dist.location)
    here = os.path.normcase(__file__)
    if not here.startswith(os.path.join(dist_loc, 'sdem')):
        # not installed, but there is another version that *is*
        raise DistributionNotFound
    else:
        __version__ = _dist.version

except DistributionNotFound:
    __version__ = 'Please install this project with setup.py'

#__version__ = get_distribution('sdem').version
