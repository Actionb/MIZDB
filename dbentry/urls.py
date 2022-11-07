from django.urls import include, path


from dbentry.views import SiteSearchView


urlpatterns = [
    path('search', SiteSearchView.as_view(), name='site_search'),
    path('ac/', include('dbentry.ac.urls')),
    path('tools/', include('dbentry.tools.urls')),
]
