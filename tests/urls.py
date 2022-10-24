from django.urls import include, path
from dbentry.sites import miz_site

urlpatterns = [
    path('admin/', include('dbentry.urls')),
    path('admin/', miz_site.urls),
]
