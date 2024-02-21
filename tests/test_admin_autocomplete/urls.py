from django.urls import path

from tests.test_admin_autocomplete.admin import admin_site

urlpatterns = [path("admin/", admin_site.urls)]
