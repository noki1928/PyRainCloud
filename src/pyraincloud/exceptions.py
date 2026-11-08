"""Domain warnings.

Errors are reported with built-in ``ValueError`` / ``TypeError`` (see the error
contract in the README); warnings use a dedicated category so users can filter them.
"""


class RaincloudWarning(UserWarning):
    """Non-fatal data issue: dropped NaNs, small samples, too many points, etc."""
