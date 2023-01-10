from django.urls import include, path

urlpatterns = [
    path('ac/', include('dbentry.ac.urls')),
    path('tools/', include('dbentry.tools.urls')),
]
