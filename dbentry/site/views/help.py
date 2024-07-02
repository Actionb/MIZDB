from django.http import Http404
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


class HelpView(BaseViewMixin, TemplateView):

    def get(self, request, *args, **kwargs):
        try:
            get_template(self.get_template_names()[0])
        except TemplateDoesNotExist:
            raise Http404
        else:
            return super().get(request, *args, **kwargs)

    def get_template_names(self):
        return [f'help/{self.kwargs["page_name"]}.html']

    @property
    def title(self):
        return f"{self.kwargs['page_name'].title()} - Hilfe"
