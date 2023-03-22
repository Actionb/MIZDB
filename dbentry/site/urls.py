from django.contrib.auth.views import logout_then_login
from django.urls import path, include

from .views import Index, LoginView, ArtikelView
from dbentry.tools.views import SearchbarSearch
from .registry import miz_site


app_name = "site"
urlpatterns = [
    path('', Index.as_view(), name="index"),
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', logout_then_login, name="logout"),
    # models
    path('', include(miz_site.urls)),
    # search
    path('searchbar/', SearchbarSearch.as_view(), name='searchbar_search')
]
