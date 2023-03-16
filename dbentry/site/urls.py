from django.contrib.auth.views import logout_then_login
from django.urls import path

from .views import Index, LoginView


app_name = "site"
urlpatterns = [
    path('', Index.as_view(), name="index"),
    path('login/', LoginView.as_view(), name="login"),
    path('logout/', logout_then_login, name="logout"),
]
