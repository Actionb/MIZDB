from django.contrib.auth.views import logout_then_login, LoginView
from django.urls import path

from .views import Index


app_name = "site"
urlpatterns = [
    path('', Index.as_view(), name="index"),
    path('login/', LoginView.as_view(template_name="mizdb/login.html", next_page="mizdb:index"), name="login"),
    path('logout/', logout_then_login, name="logout"),
]
