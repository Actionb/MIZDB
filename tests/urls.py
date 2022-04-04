from django.urls import path

from tests.case import test_site

urlpatterns = [
    path('admin/', test_site.urls)
]
