from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView


class LoginView(auth_views.LoginView):
    template_name = "mizdb/registration/login.html"
    next_page = reverse_lazy("mizdb:index")


class Index(TemplateView):
    template_name = "mizdb/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['has_permission'] = True
        return ctx
