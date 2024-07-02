from django.views.generic import TemplateView

from dbentry.site.views import BaseViewMixin


class HelpView(BaseViewMixin, TemplateView):
    page_name: str

    def get_template_names(self):
        return [f'help/{self.kwargs["page_name"]}.html']

    @property
    def title(self):
        return f"{self.kwargs['page_name'].title()} - Hilfe"
