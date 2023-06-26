"""
Changelist views for the MIZDB models.
"""
from django.contrib.postgres.aggregates import ArrayAgg
from django.views.generic import TemplateView
from formset.widgets import Selectize

from dbentry import models as _models
from dbentry.site.registry import register_changelist, ModelType
from dbentry.site.views.base import BaseViewMixin, SearchableListView
from dbentry.utils.text import concat_limit


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"


# @formatter:off
@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):
    model = _models.Artikel
    list_display = [
        'schlagzeile', 'zusammenfassung_list', 'seite_umfang', 'schlagwort_list',
        'ausgabe_name', 'artikel_magazin', 'kuenstler_list'
    ]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe'
        ],
        'widgets': {
            'ausgabe__magazin': Selectize(search_lookup="magazin_name__icontains"),
            'ausgabe': Selectize(search_lookup="ausgabe___name__icontains")
        },
    }

    # @formatter:off
    def seite_umfang(self, obj):
        return f"{obj.seite}{obj.seitenumfang}"
    seite_umfang.short_description = "Seite"
    seite_umfang.order_field = "seite"

    def ausgabe_name(self, obj: _models.Artikel) -> str:
        return obj.ausgabe._name
    ausgabe_name.short_description = 'Ausgabe'  # type: ignore[attr-defined]  # noqa
    ausgabe_name.order_field = 'ausgabe___name'  # type: ignore[attr-defined]  # noqa

    def zusammenfassung_list(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)
    zusammenfassung_list.short_description = 'Zusammenfassung'  # type: ignore[attr-defined]  # noqa
    zusammenfassung_list.order_field = 'zusammenfassung'  # type: ignore[attr-defined]  # noqa

    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name
    artikel_magazin.short_description = 'Magazin'  # type: ignore[attr-defined]  # noqa
    artikel_magazin.order_field = 'ausgabe__magazin__magazin_name'  # type: ignore[attr-defined]  # noqa

    def schlagwort_list(self, obj: _models.Artikel) -> str:
        return obj.schlagwort_list or self.get_empty_value_display()  # noqa
    schlagwort_list.short_description = 'Schlagwörter'  # type: ignore[attr-defined]  # noqa
    schlagwort_list.order_field = 'schlagwort_list'  # type: ignore[attr-defined]  # noqa

    def kuenstler_list(self, obj: _models.Artikel) -> str:
        return obj.kuenstler_list or self.get_empty_value_display()  # noqa
    kuenstler_list.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa
    # @formatter:on
