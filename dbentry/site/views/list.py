"""Changelist views for the MIZDB models."""
from django.views.generic import TemplateView

from dbentry import models as _models
from dbentry.autocomplete.widgets import make_widget
from dbentry.site.registry import register_changelist, ModelType
from dbentry.site.views.base import BaseViewMixin, SearchableListView
from dbentry.utils.text import concat_limit


def get_widget(model, can_add=False, can_edit=False, **kwargs):
    """Return a mizdb-tomselect autocomplete widget for the search form."""
    return make_widget(model, can_add=can_add, can_edit=can_edit, **kwargs)


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"


@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):
    model = _models.Artikel
    list_select_related = ['ausgabe', 'ausgabe__magazin']
    list_display = [
        'schlagzeile', 'zusammenfassung_list', 'seite_umfang', 'schlagwort_list',
        'ausgabe_name', 'artikel_magazin', 'kuenstler_list'
    ]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'autor', 'musiker', 'band',
            'schlagwort', 'genre', 'ort', 'spielort', 'veranstaltung', 'person',
            'seite__range'
        ],
        'widgets': {
            'ausgabe__magazin': get_widget(_models.Magazin, url="autocomplete_magazin"),
            'ausgabe': get_widget(
                _models.Ausgabe,
                url="autocomplete_ausgabe",
                tabular=True,
                attrs={"data-placeholder": 'Bitte zuerst ein Magazin auswählen'},
            ),
            'autor': get_widget(_models.Autor),
            'musiker': get_widget(_models.Musiker, tabular=True),
            'band': get_widget(_models.Band, tabular=True),
            'schlagwort': get_widget(_models.Schlagwort),
            'genre': get_widget(_models.Genre),
            'ort': get_widget(_models.Ort),
            'spielort': get_widget(_models.Spielort, tabular=True),
            'veranstaltung': get_widget(_models.Veranstaltung, tabular=True),
            'person': get_widget(_models.Person),
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
