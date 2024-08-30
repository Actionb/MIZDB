from django.contrib.auth.views import logout_then_login
from django.urls import include, path

from dbentry.site.registry import miz_site
from dbentry.site.views.auth import LoginView, PasswordChangeDoneView, PasswordChangeView
from dbentry.site.views.help import HelpIndexView, HelpView
from dbentry.site.views.list import Index, changelist_selection_sync
from dbentry.site.views.search import SearchbarSearch, SiteSearchView
from dbentry.site.views.watchlist import WatchlistView

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
    # Changelist selection
    path("cls_sync/", changelist_selection_sync, name="changelist_selection_sync"),
    path("watchlist/", WatchlistView.as_view(), name="watchlist"),
    path("hilfe/index/", HelpIndexView.as_view(), name="help_index"),
    path("hilfe/<path:page_name>/", HelpView.as_view(), name="help"),
    path("autocomplete/", include("dbentry.autocomplete.urls")),
]
