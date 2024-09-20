from django.urls import path

from tests.test_templatetags.admin import admin_site

urlpatterns = [path("test_templatetags/", admin_site.urls)]
