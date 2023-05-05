"""
'add' and 'change' views.
"""

from dbentry import models as _models

from dbentry.site.forms import ArtikelForm
from dbentry.site.registry import register_edit
from dbentry.site.views.base import BaseEditView

__all__ = [
    'ArtikelView'
]


@register_edit(_models.Artikel)
class ArtikelView(BaseEditView):
    form_class = ArtikelForm
    model = _models.Artikel
