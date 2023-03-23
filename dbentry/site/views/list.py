"""
Changelist views for the MIZDB models.
"""
from django.views.generic import TemplateView

from dbentry.site.views.base import BaseViewMixin


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"
