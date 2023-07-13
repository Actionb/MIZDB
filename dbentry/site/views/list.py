"""
Changelist views for the MIZDB models.

Declare a changelist view like this:

    @register_changelist(MyModel)
    class MyModelListView(BaseListView):
        model = MyModel

You can specify the columns to display in the list via the `list_display`
attribute:

    @register_changelist(MyModel)
    class MyModelListView(BaseListView):
        model = MyModel
        list_display = ["name", "field_2"]


Use SearchableListView to add a search form to the changelist:

    @register_changelist(MyModel)
    class MyModelListView(SearchableListView):
        model = MyModel
        search_form_kwargs = {
            "fields": ["name", "field_2"]
        }
"""
from django.views.generic import TemplateView

from dbentry import models as _models
from dbentry.autocomplete.widgets import make_widget
from dbentry.site.registry import register_changelist, ModelType
from dbentry.site.views.base import BaseViewMixin, SearchableListView
from dbentry.utils.text import concat_limit


# TODO: rework dbentry.search.forms.SearchFormFactory.formfield_for_dbfield to use
#  the mizdb-tomselect make_widget factory
# TODO: add 'actions'
# TODO: use 'display' decorator to add attributes to the view methods for list_display
#   https://docs.djangoproject.com/en/4.2/ref/contrib/admin/#the-display-decorator

def get_widget(model, can_add=False, can_edit=False, **kwargs):
    """Return a mizdb-tomselect autocomplete widget for the search form."""
    return make_widget(model, can_add=can_add, can_edit=can_edit, **kwargs)


class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"


@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):
    model = _models.Artikel
    list_display = [
        'schlagzeile', 'zusammenfassung_list', 'seite_umfang', 'schlagwort_list',
        'ausgabe_name', 'artikel_magazin', 'kuenstler_list'
    ]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'autor', 'musiker', 'band',
            'schlagwort', 'genre', 'ort', 'spielort', 'veranstaltung', 'person',
            # 'seite__range'  # FIXME: MultiValueFields bug out django-formset
        ],
        'widgets': {
            'ausgabe__magazin': get_widget(_models.Magazin, url="autocomplete_magazin"),
            'ausgabe': get_widget(
                _models.Ausgabe,
                url="autocomplete_ausgabe",
                tabular=True,
                attrs={"data-placeholder": 'Bitte zuerst ein Magazin auswählen'},
            ),
            'autor': get_widget(_models.Autor, multiple=True),
            'musiker': get_widget(_models.Musiker, tabular=True, multiple=True),
            'band__in': get_widget(_models.Band, tabular=True, multiple=True),
            'schlagwort': get_widget(_models.Schlagwort, multiple=True),
            'genre': get_widget(_models.Genre, multiple=True),
            'ort': get_widget(_models.Ort, multiple=True),
            'spielort': get_widget(_models.Spielort, tabular=True, multiple=True),
            'veranstaltung': get_widget(_models.Veranstaltung, tabular=True, multiple=True),
            'person': get_widget(_models.Person, multiple=True),
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


@register_changelist(_models.Genre, category=ModelType.STAMMDATEN)
class GenreList(SearchableListView):
    model = _models.Genre


@register_changelist(_models.Ausgabe, category=ModelType.ARCHIVGUT)
class AusgabenList(SearchableListView):
    model = _models.Ausgabe

    list_display = (
        'ausgabe_name', 'num_list', 'lnum_list', 'monat_list', 'jahr_list',
        'jahrgang', 'magazin_name', 'e_datum', 'anz_artikel', 'status'
    )
    search_form_kwargs = {
        'fields': [
            'magazin', 'status', 'ausgabejahr__jahr__range', 'ausgabenum__num__range',
            'ausgabelnum__lnum__range', 'ausgabemonat__monat__ordinal__range',
            'jahrgang', 'sonderausgabe', 'audio', 'video'
        ],
        'labels': {
            'ausgabejahr__jahr__range': 'Jahr',
            'ausgabenum__num__range': 'Nummer',
            'ausgabelnum__lnum__range': 'Lfd. Nummer',
            'ausgabemonat__monat__ordinal__range': 'Monatsnummer',
            'audio': 'Audio (Beilagen)',
            'video': 'Video (Beilagen)'
        },
        'widgets': {
            'magazin': get_widget(_models.Magazin, url="autocomplete_magazin"),
            'audio': get_widget(_models.Audio),
            'video': get_widget(_models.Video)
        },
    }

    # @formatter:off
    def ausgabe_name(self, obj: _models.Ausgabe) -> str:
        return obj._name
    ausgabe_name.short_description = 'Ausgabe'  # type: ignore[attr-defined]  # noqa
    ausgabe_name.order_field = '_name'  # type: ignore[attr-defined]  # noqa

    def magazin_name(self, obj: _models.Ausgabe) -> str:
        return obj.magazin.magazin_name
    magazin_name.short_description = 'Magazin'  # type: ignore[attr-defined]  # noqa
    magazin_name.order_field = 'magazin__magazin_name'  # type: ignore[attr-defined]  # noqa

    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        return obj.anz_artikel  # added by annotations  # noqa
    anz_artikel.short_description = 'Anz. Artikel'  # type: ignore[attr-defined]  # noqa
    anz_artikel.order_field = 'anz_artikel'  # type: ignore[attr-defined]  # noqa

    def jahr_list(self, obj: _models.Ausgabe) -> str:
        return obj.jahr_list  # added by annotations  # noqa
    jahr_list.short_description = 'Jahre'  # type: ignore[attr-defined]  # noqa
    jahr_list.order_field = 'jahr_list'  # type: ignore[attr-defined]  # noqa

    def num_list(self, obj: _models.Ausgabe) -> str:
        return obj.num_list  # added by annotations  # noqa
    num_list.short_description = 'Nummer'  # type: ignore[attr-defined]  # noqa
    num_list.order_field = 'num_list'  # type: ignore[attr-defined]  # noqa

    def lnum_list(self, obj: _models.Ausgabe) -> str:
        return obj.lnum_list  # added by annotations  # noqa
    lnum_list.short_description = 'lfd. Nummer'  # type: ignore[attr-defined]  # noqa
    lnum_list.order_field = 'lnum_list'  # type: ignore[attr-defined]  # noqa

    def monat_list(self, obj: _models.Ausgabe) -> str:
        return obj.monat_list  # added by annotations  # noqa
    monat_list.short_description = 'Monate'  # type: ignore[attr-defined]  # noqa
    # @formatter:on
