from django.urls import path

from DBentry.maint.views import DuplicateObjectsView, DuplicateModelSelectView

urlpatterns = [
    path('dupes/<str:model_name>/', DuplicateObjectsView.as_view(), name='dupes'),
    path('dupes/', DuplicateModelSelectView.as_view(), name='dupes_select'),
]
