from django.urls import include, path

from dbentry.bulk.views import BulkAusgabe
from dbentry.views import SiteSearchView, Watchlist

admin_tools_urls = [
    path('bulk_ausgabe', BulkAusgabe.as_view(), name='bulk_ausgabe'),
    path('watchlist', Watchlist.as_view(), name='miz_watchlist'),
]

urlpatterns = [
    path('search', SiteSearchView.as_view(), name='site_search'),
    path('ac/', include('dbentry.ac.urls')),
    path('tools/', include(admin_tools_urls)),
    path('maint/', include('dbentry.maint.urls')),
    path('', include('watchlist.urls'))
]
