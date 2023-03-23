from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from formset.views import FormViewMixin

from dbentry.site.views import BaseViewMixin


class LoginView(FormViewMixin, auth_views.LoginView):
    template_name = "mizdb/auth/login.html"
    success_url = next_page = reverse_lazy("mizdb:index")


class PasswordChangeView(FormViewMixin, BaseViewMixin, auth_views.PasswordChangeView):
    template_name = "mizdb/base_form.html"
    success_url = reverse_lazy("mizdb:password_change_done")


class PasswordChangeDoneView(FormViewMixin, BaseViewMixin, auth_views.PasswordChangeDoneView):
    template_name = "mizdb/auth/password_change_done.html"
