from django.urls import include, path

from dbentry.admin.site import miz_site

urlpatterns = [
    path("admin/", miz_site.urls),  # needed for links to the admin page
    path("", include("dbentry.site.urls")),
]
