from django.conf.urls import url,  include

from .views import ACBase, ACBuchband, ACCreateable, ACAusgabe

autocomplete_patterns = [
    url(r'^buch/$', ACBuchband.as_view(), name='acbuchband'), 
    url(r'^ausgabe/$', ACAusgabe.as_view(), name='acausgabe')
]

urlpatterns = [
    url(r'', include(autocomplete_patterns)),
    url(r'^(?P<model_name>\w+)/(?P<create_field>\w+)/$', ACBase.as_view(), name='accapture'), 
    url(r'^(?P<model_name>\w+)/$', ACCreateable.as_view(), name='accapture'), #NOTE: why does this have the same name as the previous url?
]
