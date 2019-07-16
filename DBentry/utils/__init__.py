
from DBentry.utils.admin import *  # NOQA
from DBentry.utils.copyrelated import *  # NOQA
from DBentry.utils.dates import *  # NOQA
from DBentry.utils.debug import *  # NOQA
from DBentry.utils.inspect import *  # NOQA
from DBentry.utils.jquery import *  # NOQA
from DBentry.utils.merge import *  # NOQA
from DBentry.utils.models import *  # NOQA
from DBentry.utils.text import *  # NOQA

def flatten_dict(d, exclude=[]):
    #TODO: this doesnt test that 'd' is a dict!
    #NOTE: after the rework of MIZQuerySet.values_dict this may be unused
    rslt = {}
    for k, v in d.items():
        if isinstance(v, dict):
            rslt[k] = flatten_dict(v, exclude)
        elif k not in exclude and isinstance(v, Iterable) and not isinstance(v, str) and len(v)==1:
            # TODO: either use is_iterable or also test for bytes instances
            rslt[k] = v[0]
        else:
            rslt[k] = v
    return rslt
    
def nfilter(filters, iterable):
    """Apply every filter function in 'filters' to 'iterable'."""
    def filter_func(item):
        if not filters:
            return True
        return all(filter(item) for filter in filters)
    return filter(filter_func, iterable)
    
