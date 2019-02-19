from django.conf.urls import url,  include


from DBentry.views import FavoritenView
from DBentry.bulk.views import BulkAusgabe

admin_tools_urls = [
    url(r'^bulk_ausgabe/$', BulkAusgabe.as_view(), name='bulk_ausgabe'), 
    url(r'^favoriten/$', FavoritenView.as_view(), name='favoriten'), 
    #url(r'', include('DBentry.ie.urls')) # excluded because DBentry.ie.name_utils does horrid things during import
]

urlpatterns = [
    url(r'^ac/',  include('DBentry.ac.urls')), 
    url(r'^tools/', include(admin_tools_urls)), 
    url(r'^maint/', include('DBentry.maint.urls')), 
    url(r'^help/', include('DBentry.help.urls')), 
]
