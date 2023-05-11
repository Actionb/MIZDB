"""
Changelist views for the MIZDB models.
"""
from django.contrib.postgres.aggregates import ArrayAgg
from django.views.generic import TemplateView
from formset.widgets import Selectize, SelectizeMultiple

from dbentry import models as _models
from dbentry.site.registry import register_changelist, ModelType
from dbentry.site.views.base import BaseViewMixin, SearchableListView
from dbentry.utils.text import concat_limit


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"


@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):
    model = _models.Artikel
    list_select_related = ['ausgabe', 'ausgabe__magazin']
    list_display = [
        'schlagzeile', 'zusammenfassung_string', 'seite_string', 'schlagwort_string',
        'ausgabe_name', 'artikel_magazin', 'kuenstler_string'
    ]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'autor', 'musiker', 'band',
            'schlagwort', 'genre', 'ort', 'spielort', 'veranstaltung', 'person',
            'seite__range'
        ],
        'widgets': {
            'ausgabe__magazin': Selectize(search_lookup="magazin_name__icontains", placeholder=''),
            'ausgabe': Selectize(
                search_lookup="ausgabe___name__icontains",
                filter_by={'ausgabe__magazin': 'magazin_id'},
                placeholder='Bitte zuerst ein Magazin auswählen',
            ),
            'autor': SelectizeMultiple(search_lookup='_name__icontains', placeholder=''),
            'musiker': SelectizeMultiple(search_lookup='kuenstler_name__icontains', placeholder=''),
            'band': SelectizeMultiple(search_lookup="band_name__icontains", placeholder=''),
            'schlagwort': SelectizeMultiple(search_lookup='schlagwort__icontains', placeholder=''),
            'genre': SelectizeMultiple(search_lookup='genre__icontains', placeholder=''),
            'ort': SelectizeMultiple(search_lookup='_name__icontains', placeholder=''),
            'spielort': SelectizeMultiple(search_lookup='_name__icontains', placeholder=''),
            'veranstaltung': SelectizeMultiple(search_lookup='name__icontains', placeholder=''),
            'person': SelectizeMultiple(search_lookup='_name__icontains', placeholder=''),
        },
    }

    def get_changelist_annotations(self):
        return {
            'schlagwort_list': ArrayAgg(
                'schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort'
            ),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'
            ),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name'
            )
        }

    # @formatter:off
    def seite_string(self, obj):
        return f"{obj.seite}{obj.seitenumfang}"
    seite_string.short_description = "Seite"
    seite_string.order_field = "seite"

    def ausgabe_name(self, obj: _models.Artikel) -> str:
        return obj.ausgabe._name
    ausgabe_name.short_description = 'Ausgabe'  # type: ignore[attr-defined]  # noqa
    ausgabe_name.order_field = 'ausgabe___name'  # type: ignore[attr-defined]  # noqa

    def zusammenfassung_string(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)
    zusammenfassung_string.short_description = 'Zusammenfassung'  # type: ignore[attr-defined]  # noqa
    zusammenfassung_string.order_field = 'zusammenfassung'  # type: ignore[attr-defined]  # noqa

    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name
    artikel_magazin.short_description = 'Magazin'  # type: ignore[attr-defined]  # noqa
    artikel_magazin.order_field = 'ausgabe__magazin__magazin_name'  # type: ignore[attr-defined]  # noqa

    def schlagwort_string(self, obj: _models.Artikel) -> str:
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display()  # noqa
    schlagwort_string.short_description = 'Schlagwörter'  # type: ignore[attr-defined]  # noqa
    schlagwort_string.order_field = 'schlagwort_list'  # type: ignore[attr-defined]  # noqa

    def kuenstler_string(self, obj: _models.Artikel) -> str:
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()  # noqa
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa
    # @formatter:on
