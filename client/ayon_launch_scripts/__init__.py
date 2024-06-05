""" Addon class definition and Settings definition must be imported here.

If addon class or settings definition won't be here their definition won't
be found by OpenPype discovery.
"""

from .addon import LaunchScriptsAddon
from .version import __version__

__all__ = ("LaunchScriptsAddon", "__version__")
