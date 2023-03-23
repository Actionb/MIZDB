from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from formset.views import FormViewMixin


class LoginView(FormViewMixin, auth_views.LoginView):
    template_name = "mizdb/registration/login.html"
    success_url = next_page = reverse_lazy("mizdb:index")
