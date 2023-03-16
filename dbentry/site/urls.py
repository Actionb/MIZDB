from django.contrib.auth.views import logout_then_login
from django.urls import path

from .views import Index, LoginView, ArtikelView

app_name = "site"
urlpatterns = [
    path('', Index.as_view(), name="index"),
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', logout_then_login, name="logout"),
    # models
    path('artikel/add', ArtikelView.as_view(), name='dbentry_artikel_add')
]
