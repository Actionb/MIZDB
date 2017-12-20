from django.urls import reverse, resolve

from .base import *

from DBentry.views import *
from DBentry.maint.views import *
from DBentry.ie.views import *
from DBentry.ac.views import *
from DBentry.bulk.views import *


def setup_view(view, request, *args, **kwargs):
    view.request = request
    view.args = args
    view.kwargs = kwargs
    return view
    
def setup_wizard_view(view, request, *args, **kwargs):
    view.request = request
    for k, v in view.get_initkwargs().items():
        setattr(view, k, v)
    view.args = args
    view.kwargs = kwargs
    view.dispatch(request, **view.kwargs) # WizardView sets a couple of attributes during dispatch (steps,storage,...)
    return view

class ViewTestCase(SuperUserTestCase):
    pass
