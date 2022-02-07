import time

from django.db import DEFAULT_DB_ALIAS, connections
from django.test.utils import CaptureQueriesContext


def timethis(func, *args, **kwargs):
    """Return the time needed to run func with the given args and kwargs."""
    ts = time.time()
    func(*args, **kwargs)
    te = time.time()
    return te - ts


def num_queries(func=None, *args, **kwargs):
    """Expose the functionality of assertNumQueries to use outside of tests."""
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    conn = connections[using]

    context = CaptureQueriesContext(conn)
    if func is None:
        # Return the context manager so the caller can use it.
        return context

    with context as n:
        func(*args, **kwargs)
    return len(n)
