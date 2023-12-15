"""Utility functions and helpers."""
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Union


def nfilter(filters: Iterable[Callable], iterable: Iterable) -> Iterator:
    """Apply every filter function in ``filters`` to ``iterable``."""

    def filter_func(item: Any):
        if not filters:
            return True
        return all(f(item) for f in filters)

    return filter(filter_func, iterable)


def add_attrs(**kwargs):
    """Add the given kwargs to the decorated object's attributes."""

    def inner(obj):
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj

    return inner


def flatten(iterable: Iterable) -> Union[list, Iterable]:
    """Flatten a nested iterable. Does not flatten strings."""

    def can_flatten(obj):
        return isinstance(obj, Iterable) and not isinstance(obj, str)

    if not can_flatten(iterable):
        return iterable
    flattened = []
    for subiterable in iterable:
        if can_flatten(subiterable):
            flattened.extend(flatten(subiterable))
        else:
            flattened.append(subiterable)
    return flattened
