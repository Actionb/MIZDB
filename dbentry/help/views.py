from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


class HelpIndex(BaseViewMixin, TemplateView):
    title = "Hilfe"
    template_name = "help/hauptseite.html"


class HelpView(BaseViewMixin, TemplateView):
    help_title = ""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.help_title = self.kwargs["title"].lower()

    def dispatch(self, request, *args, **kwargs):
        try:
            # Test if the template exists. If it doesn't, raise 404.
            get_template(self.get_help_template_name(self.help_title))
        except TemplateDoesNotExist:
            raise Http404(f"Hilfe Seite für '{self.help_title.title()}' nicht gefunden")
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Hilfe: {self.help_title.title()}"
        return ctx

    def get_help_template_name(self, title):
        return f"help/{title}.html"

    def get_template_names(self):
        return [self.get_help_template_name(self.help_title)]
