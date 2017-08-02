from django.conf.urls import url,  include
from .autocomplete.views import *

from .views import *

urlpatterns = [
    url(r'ac/', include('DBentry.autocomplete.urls')),
]
