from django.conf.urls import url,  include

from .views import ACCapture, ACBase, ACBuchband, ACCreateable

autocomplete_patterns = [
    url(r'^buch/$', ACBuchband.as_view(), name='acbuchband')
]

wip = [ 
]

autocomplete_patterns += wip

urlpatterns = [
    url(r'', include(autocomplete_patterns)),
    url(r'^(?P<model_name>\w+)/(?P<create_field>\w+)/$', ACCapture.as_view(), name='accapture'), 
    url(r'^(?P<model_name>\w+)/$', ACCreateable.as_view(), name='accapture'), 
]
