from django.contrib import messages
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


class HelpIndex(BaseViewMixin, TemplateView):
    title = "Hilfe"
    template_name = "help/index.html"


class HelpView(BaseViewMixin, TemplateView):
    help_title = ""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.help_title = self.kwargs["title"]

    def dispatch(self, request, *args, **kwargs):
        try:
            # Test if the template exists. If it doesn't, redirect to the index.
            get_template(self.get_help_template_name(self.help_title))
        except TemplateDoesNotExist:
            messages.add_message(
                request,
                level=messages.WARNING,
                message=f"Hilfe Seite für '{self.help_title.title()}' nicht gefunden",
            )
            return redirect("help_index")
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
