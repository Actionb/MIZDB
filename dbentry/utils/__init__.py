from dbentry.utils.admin import *  # NOQA
from dbentry.utils.copyrelated import *  # NOQA
from dbentry.utils.dates import *  # NOQA
from dbentry.utils.debug import *  # NOQA
from dbentry.utils.inspect import *  # NOQA
from dbentry.utils.merge import *  # NOQA
from dbentry.utils.models import *  # NOQA
from dbentry.utils.text import *  # NOQA


def nfilter(filters, iterable):
    """Apply every filter function in 'filters' to 'iterable'."""
    def filter_func(item):
        if not filters:
            return True
        return all(f(item) for f in filters)
    return filter(filter_func, iterable)
