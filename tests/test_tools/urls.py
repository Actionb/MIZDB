from django.urls import path

from dbentry.tools.views import DuplicateModelSelectView, DuplicateObjectsView, MIZSiteSearch, UnusedObjectsView

from .admin import admin_site

urlpatterns = [
    path("test_tools/", admin_site.urls),
    path("search/", MIZSiteSearch.as_view(), name="site_search"),
    path("dupes/<str:model_name>/", DuplicateObjectsView.as_view(admin_site=admin_site), name="dupes"),
    path("dupes/", DuplicateModelSelectView.as_view(admin_site=admin_site), name="dupes_select"),
    path("unused/", UnusedObjectsView.as_view(admin_site=admin_site), name="find_unused"),
]
