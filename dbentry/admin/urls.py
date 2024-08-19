from django.urls import include, path

urlpatterns = [
    path("ac/", include("dbentry.admin.autocomplete.urls")),
    path("tools/", include("dbentry.tools.urls", "tools")),
]
