from django.urls import include, path

from dbentry.admin.site import miz_site

urlpatterns = [
    path('admin/', include('dbentry.urls')),
    path('admin/', miz_site.urls),
    path('', include('dbentry.site.urls'))
]
