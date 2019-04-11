from django.urls import path,  include

from DBentry.views import FavoritenView
from DBentry.bulk.views import BulkAusgabe

admin_tools_urls = [
    path('bulk_ausgabe/', BulkAusgabe.as_view(), name='bulk_ausgabe'), 
    path('favoriten/', FavoritenView.as_view(), name='favoriten'), 
    #url(r'', include('DBentry.ie.urls')) # excluded because DBentry.ie.name_utils does horrid things during import
]

urlpatterns = [
    path('ac/',  include('DBentry.ac.urls')), 
    path('tools/', include(admin_tools_urls)), 
    path('maint/', include('DBentry.maint.urls')), 
    path('help/', include('DBentry.help.urls')), 
]
