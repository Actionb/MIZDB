from django.urls import include, path

# TODO: dal autocompletes should route under admin/autocomplete/, while
#  the site autocompletes should just be autocomplete/

urlpatterns = [
    path("ac/", include("dbentry.admin.autocomplete.urls")),
    path("tools/", include("dbentry.tools.urls", "tools")),
    path("autocomplete/", include("dbentry.autocomplete.urls")),
]
