from django.urls import path, include

from dbentry.sites import miz_site

urlpatterns = [
    path('admin/', miz_site.urls),  # needed for links to the admin page
    path('', include('dbentry.site.urls')),
]
