from django.urls import path

from .test_views import admin_site

urlpatterns = [path('test_actions/', admin_site.urls)]
