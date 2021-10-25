# noinspection SpellCheckingInspection
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
import os

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from dbentry.sites import miz_site

urlpatterns = [
    path('admin/', miz_site.urls),
    path('admin/', include('dbentry.urls')),

]

if settings.DEBUG:
    urlpatterns += static(prefix=settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# TODO: why not include this under the above condition (debug==True)?
if os.environ.get('DJANGO_DEVELOPMENT') in ('true', 'True', '1'):
    # Add django debug toolbar URLs:
    try:
        # noinspection PyUnresolvedReferences
        import debug_toolbar
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))
    except ImportError as e:
        # TODO: spit out warning
        pass

handler403 = 'dbentry.views.MIZ_permission_denied_view'
