"""MIZDB URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url,  include
from django.contrib import admin

from itertools import chain

from DBentry.ie.urls import import_urls
from DBentry.urls import admin_tools_urls
urls = admin.site.urls[0]
for u in chain(import_urls, admin_tools_urls):
    u.callback = admin.site.admin_view(u.callback)
    urls.insert(0, u)

urlpatterns = [
    url(r'^mizdb/', include('DBentry.urls')), # includes the autocomplete-patterns
    url(r'^admin/', (urls, admin.site.urls[1], admin.site.urls[2])),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(prefix = settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
