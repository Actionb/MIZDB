from django.conf.urls import url 


# prompt the registration of all model/form helptexts
from .models import *
from .forms import *

from .registry import halp
urlpatterns = [url(r'', halp.urls)]

