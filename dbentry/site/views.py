from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.views.generic import TemplateView


class LoginView(auth_views.LoginView):
    template_name = "mizdb/registration/login.html"
    next_page = reverse_lazy("mizdb:index")


class MIZContextMixin:
    """A mixin that provides context shared by all views."""
    title = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['title'] = self.title
        ctx['wiki_url'] = 'http://serv01/wiki/Hauptseite'
        return ctx


class Index(MIZContextMixin, TemplateView):
    title = "Index"

    template_name = "mizdb/index.html"

    def get_context_data(self, **kwargs):
        from dbentry import models as _models
        ctx = super().get_context_data(**kwargs)
        ctx['model_groups'] = [
            ('Archivgut', [_models.Ausgabe._meta, _models.Artikel._meta]),
            ('Stammdaten', [_models.Band._meta, _models.Musiker._meta, _models.Magazin._meta]),
            ('Sonstige', [_models.Lagerort._meta])
        ]
        return ctx
