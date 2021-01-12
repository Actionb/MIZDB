from django.urls import path, include

from dbentry.views import SiteSearchView
from dbentry.bulk.views import BulkAusgabe, BulkAusgabeHelp

admin_tools_urls = [
    path('bulk_ausgabe/', BulkAusgabe.as_view(), name='bulk_ausgabe'),
]

help_urls = [
    path('bulk_ausgabe', BulkAusgabeHelp.as_view(), name='help_bulk_ausgabe'),
]

urlpatterns = [
    path('search', SiteSearchView.as_view(), name='site_search'),
    path('ac/', include('dbentry.ac.urls')),
    path('tools/', include(admin_tools_urls)),
    path('maint/', include('dbentry.maint.urls')),
    path('help/', include(help_urls))
]
