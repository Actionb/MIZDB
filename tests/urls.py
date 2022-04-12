from django.urls import include, path
from dbentry.sites import miz_site
# TODO: delete this urls.py? Tests should define their own URLs.

urlpatterns = [
    path('admin/', include('dbentry.urls')),
    path('admin/', miz_site.urls),
]
