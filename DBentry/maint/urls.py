from django.conf.urls import url 
from .views import MaintView,  UnusedObjectsView
from DBentry.models import * 
 
urlpatterns = [ 
    url(r'main/$', MaintView.as_view(), name='maint_main'),  
    url(r'(?P<model>\w+)/lte(?P<lte>[0-9]+)/$', UnusedObjectsView.as_view(), name='unused_objects'), 
] 
