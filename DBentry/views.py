from django.shortcuts import render
from django.views.generic import *
from django.http import HttpResponse
from django.forms import formset_factory

from .models import *
from .forms import *
from .helper import *

from dal import autocomplete

# Create your views here
from django.views.decorators.http import require_http_methods

