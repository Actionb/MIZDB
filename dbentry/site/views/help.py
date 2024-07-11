from urllib.parse import unquote

from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin



class HelpIndexView(BaseViewMixin, TemplateView):
    title = "Hilfe"
    template_name = "help/index.html"


class HelpView(BaseViewMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        try:
            get_template(self.get_template_names()[0])
        except TemplateDoesNotExist:
            raise Http404
        else:
            return super().get(request, *args, **kwargs)

    def get_template_names(self):
        template_name = unquote(self.kwargs["page_name"])
        return [f'help/{template_name}.html']

    @property
    def title(self):
        return f"{unquote(self.kwargs['page_name']).title()} - Hilfe"
