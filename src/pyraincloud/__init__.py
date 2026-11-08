"""PyRainCloud: rain cloud plots from pandas DataFrames in one call.

>>> import pyraincloud as rc
>>> fig, ax = rc.raincloud(data=df, x="group", y="value")  # doctest: +SKIP
"""

from .exceptions import RaincloudWarning
from .plot import raincloud

__version__ = "0.1.0"

__all__ = ["RaincloudWarning", "__version__", "raincloud"]
