from django.conf.urls import url 
 
from .views import ModelHelpView, HelpIndexView, BulkFormAusgabeHelpView
 
urlpatterns = [ 
    url(r'bulk_ausgabe/$',  BulkFormAusgabeHelpView.as_view(), name='help_bulk'), 
    url(r'(?P<model_name>\w+)/$',  ModelHelpView.as_view(), name='help'), 
    url('', HelpIndexView.as_view(), name = 'help_index'),  
] 
