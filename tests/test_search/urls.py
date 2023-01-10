from django.urls import path

from .admin import admin_site

urlpatterns = [path('test_search/', admin_site.urls)]
