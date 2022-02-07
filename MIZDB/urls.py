# noinspection GrazieInspection
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
import warnings

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from dbentry.sites import miz_site

urlpatterns = [
    path('admin/', include('dbentry.urls')),
    path('admin/', miz_site.urls),

]

if settings.DEBUG:
    urlpatterns += static(prefix=settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.environ.get('DJANGO_DEVELOPMENT'):
    # Add django debug toolbar URLs:
    try:
        # noinspection PyUnresolvedReferences
        import debug_toolbar
    except ModuleNotFoundError as e:
        warnings.warn(f"Could not import django debug toolbar when setting up URL configs: {e!s}")
    else:
        urlpatterns.append(path('__debug__/', include(debug_toolbar.urls)))

handler403 = 'dbentry.views.MIZ_permission_denied_view'
