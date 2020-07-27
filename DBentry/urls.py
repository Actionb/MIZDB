from django.urls import path, include

from DBentry.bulk.views import BulkAusgabe, BulkAusgabeHelp
from DBentry.views import FavoritenView

admin_tools_urls = [
    path('bulk_ausgabe/', BulkAusgabe.as_view(), name='bulk_ausgabe'),
    path('favoriten/', FavoritenView.as_view(), name='favoriten'),
]

help_urls = [
    path('bulk_ausgabe', BulkAusgabeHelp.as_view(), name='help_bulk_ausgabe'),
]

urlpatterns = [
    path('ac/', include('DBentry.ac.urls')),
    path('tools/', include(admin_tools_urls)),
    path('maint/', include('DBentry.maint.urls')),
    path('help/', include(help_urls))
]
