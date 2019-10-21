from django.conf.urls import url

# TODO: import (or rather prompt the registration) of the models and forms
# should be done in halp.urls or the like

# Prompt the registration of all model/form helptexts by importing.
from .models import *
from .forms import *

from .registry import halp
urlpatterns = [url(r'', halp.urls)]
