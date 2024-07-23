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
from django.views import defaults

from dbentry.admin.site import miz_site

urlpatterns = [
    # admin autocomplete and admin tool views:
    path("admin/", include("dbentry.admin.urls")),
    # admin site:
    path("admin/", miz_site.urls),
    # MIZDB site (non-admin):
    path("", include("dbentry.site.urls")),
    # watchlist URLs:
    path("mizdb_watchlist/", include("mizdb_watchlist.urls")),
]

if settings.DEBUG:
    urlpatterns += static(prefix=settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if os.environ.get("DJANGO_DEVELOPMENT", False):
    # Add django debug toolbar URLs:
    try:
        # noinspection PyPackageRequirements
        import debug_toolbar
    except ModuleNotFoundError as e:
        warnings.warn(f"Could not import django debug toolbar when setting up URL configs: {e!s}")
    else:
        urlpatterns.append(path("__debug__/", include(debug_toolbar.urls)))


def page_not_found(request, exception, template_name="mizdb/404.html"):  # pragma: no cover
    if request.path_info.startswith("/admin"):
        # Show the admin 404 if requesting an admin page.
        template_name = "admin/404.html"
    return defaults.page_not_found(request, exception, template_name)


handler403 = "dbentry.site.views.auth.permission_denied_view"
handler404 = page_not_found
