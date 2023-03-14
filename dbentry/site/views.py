from django.contrib.auth.views import LoginView as BaseLoginView
from django.urls import reverse_lazy
from django.views.generic import TemplateView


class Index(TemplateView):
    template_name = "mizdb/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['has_permission'] = True
        return ctx


# class LoginView(BaseLoginView):
#     template_name = "site/login.html"
#     success_url = reverse_lazy("site:index")
