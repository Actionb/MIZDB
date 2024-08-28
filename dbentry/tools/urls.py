from django.urls import path

from dbentry.tools.bulk.views import BulkAusgabe
from dbentry.tools.views import DuplicateModelSelectView, DuplicateObjectsView, MIZSiteSearch, UnusedObjectsView

app_name = "tools"
urlpatterns = [
    path("search/", MIZSiteSearch.as_view(), name="site_search"),
    path("dupes/<str:model_name>/", DuplicateObjectsView.as_view(), name="dupes"),
    path("dupes/", DuplicateModelSelectView.as_view(), name="dupes_select"),
    path("unused/", UnusedObjectsView.as_view(), name="find_unused"),
    path("bulk_ausgabe/", BulkAusgabe.as_view(), name="bulk_ausgabe"),
]
