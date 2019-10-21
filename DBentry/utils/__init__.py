from DBentry.utils.admin import *  # NOQA
from DBentry.utils.copyrelated import *  # NOQA
from DBentry.utils.dates import *  # NOQA
from DBentry.utils.debug import *  # NOQA
from DBentry.utils.inspect import *  # NOQA
from DBentry.utils.jquery import *  # NOQA
from DBentry.utils.merge import *  # NOQA
from DBentry.utils.models import *  # NOQA
from DBentry.utils.text import *  # NOQA


def nfilter(filters, iterable):
    """Apply every filter function in 'filters' to 'iterable'."""
    def filter_func(item):
        if not filters:
            return True
        return all(filter(item) for filter in filters)
    return filter(filter_func, iterable)
