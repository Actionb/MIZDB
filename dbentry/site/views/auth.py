from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from dbentry.site.views.base import BaseViewMixin


class LoginView(BaseViewMixin, auth_views.LoginView):
    template_name = "mizdb/auth/login.html"
    success_url = next_page = reverse_lazy("index")
    title = "Anmelden"


class PasswordChangeView(BaseViewMixin, auth_views.PasswordChangeView):
    template_name = "mizdb/auth/auth_form.html"
    success_url = reverse_lazy("password_change_done")
    title = "Passwort ändern"


class PasswordChangeDoneView(BaseViewMixin, auth_views.PasswordChangeDoneView):
    template_name = "mizdb/auth/password_change_done.html"
    title = "Passwort geändert"


class PermissionDeniedView(BaseViewMixin, TemplateView):
    template_name = "mizdb/auth/403.html"

    def get_context_data(self, **kwargs):  # pragma: no cover
        ctx = super().get_context_data(**kwargs)
        ctx["exception"] = (
            str(self.kwargs.get("exception")) or "Sie haben nicht die erforderliche Berechtigung diese Seite zu sehen."
        )
        return ctx


# Provide a callable that can be imported from the ROOT URL CONF
permission_denied_view = PermissionDeniedView.as_view()
