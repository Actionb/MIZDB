from django.urls import path, include

from dbentry.sites import miz_site

urlpatterns = [
    path('admin/', include('dbentry.urls')),  # required for the site_search url (used in search_modal)
    path('admin/', miz_site.urls),  # needed for links to the admin page
    path('', include('dbentry.site.urls')),
]
