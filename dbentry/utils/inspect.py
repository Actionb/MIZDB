from collections import Iterable


def is_iterable(obj):
    """Return True if obj is iterable but not a bytes or a string instance."""
    return isinstance(obj, Iterable) and not isinstance(obj, (bytes, str))
