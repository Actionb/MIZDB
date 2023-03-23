from django.contrib.auth.views import logout_then_login
from django.urls import path, include

from dbentry.site.registry import miz_site
from dbentry.site.views import Index, LoginView
from dbentry.tools.views import SearchbarSearch

app_name = "site"
urlpatterns = [
    path('', Index.as_view(), name="index"),
    path('', include(miz_site.urls)),
    # Auth
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', logout_then_login, name="logout"),
    # Search
    path('searchbar/', SearchbarSearch.as_view(), name='searchbar_search'),
]
