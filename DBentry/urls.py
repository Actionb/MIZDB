from django.urls import path, include

from DBentry.bulk.views import BulkAusgabe
from DBentry.views import FavoritenView

admin_tools_urls = [
    path('bulk_ausgabe/', BulkAusgabe.as_view(), name='bulk_ausgabe'),
    path('favoriten/', FavoritenView.as_view(), name='favoriten'),
]

urlpatterns = [
    path('ac/', include('DBentry.ac.urls')),
    path('tools/', include(admin_tools_urls)),
    path('maint/', include('DBentry.maint.urls')),
    path('help/', include('DBentry.help.urls')),
]
