from collections import Iterable
from typing import Any


def is_iterable(obj: Any) -> bool:
    """Return True if obj is iterable but not a bytes or a string instance."""
    return isinstance(obj, Iterable) and not isinstance(obj, (bytes, str))
