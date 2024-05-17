from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


class HelpIndex(BaseViewMixin, TemplateView):
    title = "Hilfe"
    template_name = "help/index.html"


class HelpView(BaseViewMixin, TemplateView):

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["title"] = f"Hilfe: {self.kwargs['title'].title()}"
        return ctx

    def get_template_names(self):
        # TODO: include help index as fallback?
        return [f"help/{self.kwargs['title']}.html", "help/index.html"]
