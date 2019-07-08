from collections import Iterable

def is_iterable(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (bytes, str))
