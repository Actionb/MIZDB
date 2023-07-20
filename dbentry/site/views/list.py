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
from dbentry.utils import add_attrs
from dbentry.utils.text import concat_limit


# TODO: rework dbentry.search.forms.SearchFormFactory.formfield_for_dbfield to use
#  the mizdb-tomselect make_widget factory
# TODO: add 'actions'

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
        },
    }

    @add_attrs(description="Seite", ordering="seite")
    def seite_umfang(self, obj):
        return f"{obj.seite}{obj.seitenumfang}"

    @add_attrs(description="Ausgabe", ordering="ausgabe___name")
    def ausgabe_name(self, obj: _models.Artikel) -> str:
        return obj.ausgabe._name

    @add_attrs(description="Zusammenfassung", ordering="zusammenfassung")
    def zusammenfassung_list(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)

    @add_attrs(description="Magazin", ordering="ausgabe__magazin__magazin_name")
    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name

    @add_attrs(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_list(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    def kuenstler_list(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


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
        'widgets': {'magazin': get_widget(_models.Magazin, url="autocomplete_magazin")},
    }

    @add_attrs(description="Ausgabe", ordering="_name")
    def ausgabe_name(self, obj: _models.Ausgabe) -> str:
        return obj._name

    @add_attrs(description="Magazin", ordering="magazin__magazin_name")
    def magazin_name(self, obj: _models.Ausgabe) -> str:
        return obj.magazin.magazin_name

    @add_attrs(description="Anz. Artikel", ordering="anz_artikel")
    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_artikel

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list

    @add_attrs(description="Nummer", ordering="num_list")
    def num_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.num_list

    @add_attrs(description="lfd. Nummer", ordering="lnum_list")
    def lnum_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.lnum_list

    @add_attrs(description="Monate")
    def monat_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.monat_list
