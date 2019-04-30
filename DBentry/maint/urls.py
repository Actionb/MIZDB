from django.conf.urls import url 
from .views import MaintView,  UnusedObjectsView, DuplicateObjectsView, ModelSelectView
from DBentry.models import * 
 
urlpatterns = [ 
    url(r'(?P<model>\w+)/lte(?P<lte>[0-9]+)/$', UnusedObjectsView.as_view(), name='unused_objects'), 
    url(r'dupes/(?P<model_name>\w+)/$' , DuplicateObjectsView.as_view(), name='dupes'), 
    url(r'dupes/$', ModelSelectView.as_view(title='Duplikate', next_view = 'dupes'), name='dupes_select'), 
    url(r'unused/$', ModelSelectView.as_view(title='Unbenutzt', next_view = 'unused_objects'), name='unused_select'), 
#    url(r'', MaintView.as_view(), name='maint_main'),  #TODO: I assume this is meant to be 'index' of maint
] 
