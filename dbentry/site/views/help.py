from urllib.parse import unquote

from django.contrib import messages
from django.shortcuts import redirect
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


def has_help_page(name):
    """Return whether a help page for the given name exists."""
    try:
        get_template(f"help/{name.lower()}.html")
    except TemplateDoesNotExist:
        return False
    return True


class HelpIndexView(BaseViewMixin, TemplateView):
    title = "Hilfe"
    template_name = "help/index.html"


class HelpView(BaseViewMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        try:
            if has_help_page(self.kwargs["page_name"]):
                return super().get(request, *args, **kwargs)
            else:
                messages.warning(request, f"Hilfe Seite für '{self.kwargs['page_name']}' nicht gefunden.")
        except KeyError:
            pass
        # No 'page_name' in kwargs or no template with that name exists.
        return redirect("help_index")

    def get_template_names(self):
        template_name = unquote(self.kwargs["page_name"])
        return [f"help/{template_name}.html"]

    @property
    def title(self):
        return f"{unquote(self.kwargs['page_name']).title().replace('_', ' ')} - Hilfe"
