from django.urls import path

from dbentry.maint.views import DuplicateModelSelectView, DuplicateObjectsView, UnusedObjectsView
from .admin import admin_site

urlpatterns = [
    path('test_maint/', admin_site.urls),
    path(
        'dupes/<str:model_name>/',
        DuplicateObjectsView.as_view(admin_site=admin_site),
        name='dupes'
    ),
    path('dupes/', DuplicateModelSelectView.as_view(admin_site=admin_site), name='dupes_select'),
    path('unused/', UnusedObjectsView.as_view(admin_site=admin_site), name='find_unused'),
]
