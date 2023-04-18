"""Utility functions and helpers."""

from typing import Any, Callable, Iterable, Iterator


def nfilter(filters: Iterable[Callable], iterable: Iterable) -> Iterator:
    """Apply every filter function in ``filters`` to ``iterable``."""

    def filter_func(item: Any):
        if not filters:
            return True
        return all(f(item) for f in filters)

    return filter(filter_func, iterable)
