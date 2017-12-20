from django.conf.urls import url 
from .views import * 
from DBentry.models import * 
 
urlpatterns = [ 
    url(r'main/$', MaintView.as_view(), name='maint_main'),  
    url(r'(?P<model>\w+)/lte(?P<lte>[0-9]+)/$', UnusedObjectsView.as_view(), name='unused_objects'),  
    url(r'merge/(?P<model_name>\w+)$', MergeViewWizarded.as_view(), name='merge') 
] 
