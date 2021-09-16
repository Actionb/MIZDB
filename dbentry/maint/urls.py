from django.urls import path

from dbentry.maint.views import (
    DuplicateModelSelectView, DuplicateObjectsView, UnusedObjectsView
)

urlpatterns = [
    path('dupes/<str:model_name>/', DuplicateObjectsView.as_view(), name='dupes'),
    path('dupes/', DuplicateModelSelectView.as_view(), name='dupes_select'),
    path('unused/', UnusedObjectsView.as_view(), name='find_unused'),
]
