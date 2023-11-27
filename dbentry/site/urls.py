from django.contrib.auth.views import logout_then_login
from django.urls import path, include

from dbentry.site.registry import miz_site
from dbentry.site.views.auth import LoginView, PasswordChangeView, PasswordChangeDoneView
from dbentry.site.views.list import Index
from dbentry.site.views.search import SearchbarSearch, SiteSearchView

urlpatterns = [
    path("", Index.as_view(), name="index"),
    path("", include(miz_site.urls)),
    # Auth
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", logout_then_login, name="logout"),
    path("password_change/", PasswordChangeView.as_view(), name="password_change"),
    path("password_change/done/", PasswordChangeDoneView.as_view(), name="password_change_done"),
    # Search
    path("searchbar/", SearchbarSearch.as_view(), name="searchbar_search"),
    path("search/", SiteSearchView.as_view(), name="site_search"),
]
