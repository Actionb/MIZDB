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
from dbentry.site.views.base import BaseViewMixin
from dbentry.site.views.base import SearchableListView
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
    expensive_ordering = True
    prioritize_search_ordering = False
    list_display = [
        "schlagzeile",
        "zusammenfassung_list",
        "seite_umfang",
        "schlagwort_list",
        "ausgabe_name",
        "artikel_magazin",
        "kuenstler_list",
    ]
    search_form_kwargs = {
        "fields": [
            "ausgabe__magazin",
            "ausgabe",
            "autor",
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "seite__range",
        ],
        "widgets": {
            "ausgabe__magazin": get_widget(_models.Magazin, url="autocomplete_magazin"),
            "ausgabe": get_widget(
                _models.Ausgabe,
                url="autocomplete_ausgabe",
                tabular=True,
                attrs={"data-placeholder": "Bitte zuerst ein Magazin auswählen"},
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

    @add_attrs(description="Künstler")
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
    prioritize_search_ordering = True
    ordering = ["magazin__magazin_name", "_name"]
    list_display = (
        "ausgabe_name",
        "num_list",
        "lnum_list",
        "monat_list",
        "jahr_list",
        "jahrgang",
        "magazin_name",
        "e_datum",
        "anz_artikel",
        "status",
    )
    search_form_kwargs = {
        "fields": [
            "magazin",
            "status",
            "ausgabejahr__jahr__range",
            "ausgabenum__num__range",
            "ausgabelnum__lnum__range",
            "ausgabemonat__monat__ordinal__range",
            "jahrgang",
            "sonderausgabe",
            "audio",
            "video",
        ],
        "labels": {
            "ausgabejahr__jahr__range": "Jahr",
            "ausgabenum__num__range": "Nummer",
            "ausgabelnum__lnum__range": "Lfd. Nummer",
            "ausgabemonat__monat__ordinal__range": "Monatsnummer",
            "audio": "Audio (Beilagen)",
            "video": "Video (Beilagen)",
        },
        "widgets": {"magazin": get_widget(_models.Magazin, url="autocomplete_magazin")},
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


@register_changelist(_models.Audio, category=ModelType.ARCHIVGUT)
class AudioList(SearchableListView):
    model = _models.Audio
    ordering = ["titel", "jahr", "medium"]
    list_display = ["titel", "jahr", "medium", "kuenstler_list"]
    search_form_kwargs = {
        "fields": [
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "plattenfirma",
            "medium",
            "release_id",
            "land_pressung",
        ],
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
    }

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Audio):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Ausgabe, category=ModelType.ARCHIVGUT)
class AusgabeList(SearchableListView):   # TODO: duplicate of AusgabenList above!
    model = _models.Ausgabe
    ordering = ["magazin__magazin_name", "_name"]
    list_display = (
        "ausgabe_name",
        "num_list",
        "lnum_list",
        "monat_list",
        "jahr_list",
        "jahrgang",
        "magazin_name",
        "e_datum",
        "anz_artikel",
        "status",
    )
    search_form_kwargs = {
        "fields": [
            "magazin",
            "status",
            "ausgabejahr__jahr__range",
            "ausgabenum__num__range",
            "ausgabelnum__lnum__range",
            "ausgabemonat__monat__ordinal__range",
            "jahrgang",
            "sonderausgabe",
            "audio",
            "video",
        ],
        "labels": {
            "ausgabejahr__jahr__range": "Jahr",
            "ausgabenum__num__range": "Nummer",
            "ausgabelnum__lnum__range": "Lfd. Nummer",
            "ausgabemonat__monat__ordinal__range": "Monatsnummer",
            "audio": "Audio (Beilagen)",
            "video": "Video (Beilagen)",
        },
    }

    @add_attrs(description="Ausgabe", ordering="_name")
    def ausgabe_name(self, obj: _models.Ausgabe):
        return obj._name

    @add_attrs(description="Nummer", ordering="num_list")
    def num_list(self, obj: _models.Ausgabe):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.num_list

    @add_attrs(description="lfd. Nummer", ordering="lnum_list")
    def lnum_list(self, obj: _models.Ausgabe):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.lnum_list

    @add_attrs(description="Monate")
    def monat_list(self, obj: _models.Ausgabe):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.monat_list

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.Ausgabe):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list

    @add_attrs(description="Magazin", ordering="magazin__magazin_name")
    def magazin_name(self, obj: _models.Ausgabe):
        return obj.magazin.magazin_name

    @add_attrs(description="Anz. Artikel", ordering="anz_artikel")
    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_artikel


@register_changelist(_models.Autor, category=ModelType.STAMMDATEN)
class AutorList(SearchableListView):
    model = _models.Autor
    ordering = ["_name"]
    list_display = ["autor_name", "person", "kuerzel", "magazin_string"]
    search_form_kwargs = {"fields": ["magazin", "person"]}

    @add_attrs(description="Autor", ordering="_name")
    def autor_name(self, obj: _models.Autor):
        return obj._name

    @add_attrs(description="Magazin(e)", ordering="magazin_list")
    def magazin_string(self, obj: _models.Autor):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.magazin_list or self.get_empty_value_display()


@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):  # TODO: duplicate!
    model = _models.Artikel
    ordering = ["ausgabe__magazin__magazin_name", "ausgabe___name", "seite", "schlagzeile"]
    list_display = [
        "schlagzeile",
        "zusammenfassung_string",
        "seite",
        "schlagwort_string",
        "ausgabe_name",
        "artikel_magazin",
        "kuenstler_list",
    ]
    search_form_kwargs = {
        "fields": [
            "ausgabe__magazin",
            "ausgabe",
            "autor",
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "seite__range",
        ],
        "tabular": ["ausgabe", "musiker", "band", "spielort", "veranstaltung"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }

    @add_attrs(description="Zusammenfassung", ordering="zusammenfassung")
    def zusammenfassung_string(self, obj: _models.Artikel):
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)

    @add_attrs(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_string(self, obj: _models.Artikel):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    @add_attrs(description="Ausgabe", ordering="ausgabe___name")
    def ausgabe_name(self, obj: _models.Artikel):
        return obj.ausgabe._name

    @add_attrs(description="Magazin", ordering="ausgabe__magazin__magazin_name")
    def artikel_magazin(self, obj: _models.Artikel):
        return obj.ausgabe.magazin.magazin_name

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Artikel):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Band, category=ModelType.STAMMDATEN)
class BandList(SearchableListView):
    model = _models.Band
    ordering = ["band_name"]
    list_display = ["band_name", "genre_string", "musiker_string", "orte_string"]
    search_form_kwargs = {
        "fields": ["musiker", "genre", "orte__land", "orte"],
        "labels": {"musiker": "Mitglied"},
        "tabular": ["musiker"],
    }

    @add_attrs(description="Genres", ordering="genre_list")
    def genre_string(self, obj: _models.Band):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.genre_list or self.get_empty_value_display()

    @add_attrs(description="Mitglieder", ordering="musiker_list")
    def musiker_string(self, obj: _models.Band):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.musiker_list or self.get_empty_value_display()

    @add_attrs(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Band):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()


@register_changelist(_models.Plakat, category=ModelType.ARCHIVGUT)
class PlakatList(SearchableListView):
    model = _models.Plakat
    ordering = ["titel", "datum"]
    list_display = ["titel", "plakat_id", "size", "datum_localized", "veranstaltung_string"]
    search_form_kwargs = {
        "fields": [
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "reihe",
            "datum__range",
            "signatur__contains",
        ],
        "labels": {"reihe": "Bildreihe"},
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
    }

    @add_attrs(description="Plakat ID", ordering="id")
    def plakat_id(self, obj: _models.Plakat):
        """ID of this instance, with a prefixed 'P' and padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return "P" + str(obj.pk).zfill(6)

    @add_attrs(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Plakat):
        return obj.datum.localize()

    @add_attrs(description="Veranstaltungen", ordering="veranstaltung_list")
    def veranstaltung_string(self, obj: _models.Plakat):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.veranstaltung_list or self.get_empty_value_display()


@register_changelist(_models.Buch, category=ModelType.ARCHIVGUT)
class BuchList(SearchableListView):
    model = _models.Buch
    ordering = ["titel"]
    list_display = ["titel", "seitenumfang", "autoren_string", "kuenstler_list", "schlagwort_string", "genre_string"]
    search_form_kwargs = {
        "fields": [
            "autor",
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "herausgeber",
            "verlag",
            "schriftenreihe",
            "buchband",
            "jahr",
            "ISBN",
            "EAN",
        ],
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
        "help_texts": {"autor": None},
    }

    @add_attrs(description="Autoren", ordering="autor_list")
    def autoren_string(self, obj: _models.Buch):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.autor_list or self.get_empty_value_display()

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Buch):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()

    @add_attrs(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_string(self, obj: _models.Buch):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    @add_attrs(description="Genres", ordering="genre_list")
    def genre_string(self, obj: _models.Buch):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.genre_list or self.get_empty_value_display()


@register_changelist(_models.Dokument, category=ModelType.ARCHIVGUT)
class DokumentList(SearchableListView):
    model = _models.Dokument
    ordering = ["titel"]


@register_changelist(_models.Genre, category=ModelType.STAMMDATEN)
class GenreList(SearchableListView):  # TODO: duplicate!
    model = _models.Genre
    ordering = ["genre"]
    list_display = ["genre", "alias_string"]

    @add_attrs(description="Aliase")
    def alias_string(self, obj: _models.Genre):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()


@register_changelist(_models.Magazin, category=ModelType.STAMMDATEN)
class MagazinList(SearchableListView):
    model = _models.Magazin
    ordering = ["magazin_name"]
    list_display = ["magazin_name", "short_beschreibung", "orte_string", "anz_ausgaben"]
    search_form_kwargs = {"fields": ["verlag", "herausgeber", "orte", "genre", "issn", "fanzine"]}

    @add_attrs(description="Beschreibung", ordering="beschreibung")
    def short_beschreibung(self, obj: _models.Magazin):
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")

    @add_attrs(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Magazin):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()

    @add_attrs(description="Anz. Ausgaben", ordering="anz_ausgaben")
    def anz_ausgaben(self, obj: _models.Magazin) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_ausgaben


@register_changelist(_models.Memorabilien, category=ModelType.ARCHIVGUT)
class MemorabilienList(SearchableListView):
    model = _models.Memorabilien
    ordering = ["titel"]


@register_changelist(_models.Musiker, category=ModelType.STAMMDATEN)
class MusikerList(SearchableListView):
    model = _models.Musiker
    ordering = ["kuenstler_name"]
    list_display = ["kuenstler_name", "genre_string", "band_string", "orte_string"]
    search_form_kwargs = {"fields": ["person", "genre", "instrument", "orte__land", "orte"]}

    @add_attrs(description="Genres", ordering="genre_list")
    def genre_string(self, obj: _models.Musiker):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.genre_list or self.get_empty_value_display()

    @add_attrs(description="Bands", ordering="band_list")
    def band_string(self, obj: _models.Musiker):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.band_list or self.get_empty_value_display()

    @add_attrs(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Musiker):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()


@register_changelist(_models.Person, category=ModelType.STAMMDATEN)
class PersonList(SearchableListView):
    model = _models.Person
    ordering = ["nachname", "vorname"]
    list_display = ("vorname", "nachname", "orte_string", "is_musiker", "is_autor")
    list_display_links = ["vorname", "nachname"]
    search_form_kwargs = {
        "fields": ["orte", "orte__land", "orte__bland", "gnd_id"],
        "filter_by": {"orte__bland": ("orte__land", "land_id")},
    }

    @add_attrs(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Person):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()

    @add_attrs(description="Ist Musiker", boolean=True)
    def is_musiker(self, obj: _models.Person) -> bool:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.is_musiker

    @add_attrs(description="Ist Autor", boolean=True)
    def is_autor(self, obj: _models.Person) -> bool:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.is_autor


@register_changelist(_models.Schlagwort, category=ModelType.STAMMDATEN)
class SchlagwortList(SearchableListView):
    model = _models.Schlagwort
    ordering = ["schlagwort"]
    list_display = ["schlagwort", "alias_string"]

    @add_attrs(description="Aliase", ordering="alias_list")
    def alias_string(self, obj: _models.Schlagwort):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()


@register_changelist(_models.Spielort, category=ModelType.SONSTIGE)
class SpielortList(SearchableListView):
    model = _models.Spielort
    ordering = ["name", "ort"]
    list_display = ["name", "ort"]
    search_form_kwargs = {"fields": ["ort", "ort__land"]}


@register_changelist(_models.Technik, category=ModelType.ARCHIVGUT)
class TechnikList(SearchableListView):
    model = _models.Technik
    ordering = ["titel"]


@register_changelist(_models.Veranstaltung, category=ModelType.SONSTIGE)
class VeranstaltungList(SearchableListView):
    model = _models.Veranstaltung
    ordering = ["name", "spielort", "datum"]
    list_display = ["name", "datum_localized", "spielort", "kuenstler_list"]
    search_form_kwargs = {
        "fields": ["musiker", "band", "schlagwort", "genre", "person", "spielort", "reihe", "datum__range"],
        "tabular": ["musiker", "band"],
    }

    @add_attrs(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Veranstaltung):
        return obj.datum.localize()

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Veranstaltung):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Verlag, category=ModelType.SONSTIGE)
class VerlagList(SearchableListView):
    model = _models.Verlag
    ordering = ["verlag_name", "sitz"]
    list_display = ["verlag_name", "sitz"]
    search_form_kwargs = {"fields": ["sitz", "sitz__land", "sitz__bland"], "labels": {"sitz": "Sitz"}}


@register_changelist(_models.Video, category=ModelType.ARCHIVGUT)
class VideoList(SearchableListView):
    model = _models.Video
    ordering = ["titel"]
    list_display = ["titel", "medium", "kuenstler_list"]
    search_form_kwargs = {
        "fields": [
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "medium",
            "release_id",
        ],
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
    }

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Video):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Bundesland, category=ModelType.SONSTIGE)
class BundeslandList(SearchableListView):
    model = _models.Bundesland
    ordering = ["land", "bland_name"]
    list_display = ["bland_name", "code", "land"]
    search_form_kwargs = {"fields": ["land"]}


@register_changelist(_models.Land, category=ModelType.SONSTIGE)
class LandList(SearchableListView):
    model = _models.Land
    ordering = ["land_name"]


@register_changelist(_models.Ort, category=ModelType.STAMMDATEN)
class OrtList(SearchableListView):
    model = _models.Ort
    ordering = ["land", "bland", "stadt"]
    list_display = ["stadt", "bland", "land"]
    list_display_links = ["stadt", "bland", "land"]
    search_form_kwargs = {"fields": ["land", "bland"], "forward": {"bland": "land"}}


@register_changelist(_models.Bestand, category=ModelType.SONSTIGE)
class BestandList(SearchableListView):
    model = _models.Bestand
    list_display = ["signatur", "bestand_class", "bestand_link", "lagerort", "provenienz"]
    search_form_kwargs = {"fields": ["lagerort", "provenienz", "signatur"]}

    @add_attrs(description="Art")
    def bestand_class(self, obj: _models.Bestand):
        try:
            return self._cache[obj.pk]["bestand_class"]
        except KeyError:
            return ""

    @add_attrs(description="Links")
    def bestand_link(self, obj: _models.Bestand):
        try:
            return self._cache[obj.pk]["bestand_link"]
        except KeyError:
            return ""


@register_changelist(_models.Datei, category=ModelType.ARCHIVGUT)
class DateiList(SearchableListView):
    model = _models.Datei
    ordering = ["titel"]


@register_changelist(_models.Instrument, category=ModelType.SONSTIGE)
class InstrumentList(SearchableListView):
    model = _models.Instrument
    ordering = ["instrument"]
    list_display = ["instrument", "kuerzel"]


@register_changelist(_models.Herausgeber, category=ModelType.SONSTIGE)
class HerausgeberList(SearchableListView):
    model = _models.Herausgeber
    ordering = ["herausgeber"]


@register_changelist(_models.Brochure, category=ModelType.ARCHIVGUT)
class BrochureList(SearchableListView):
    model = _models.Brochure
    list_display = ["titel", "zusammenfassung", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "schlagwort", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }

    @add_attrs(description="Jahre", ordering="jahr_min")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@register_changelist(_models.Katalog, category=ModelType.ARCHIVGUT)
class KatalogList(SearchableListView):
    model = _models.Katalog
    list_display = ["titel", "zusammenfassung", "art", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }

    @add_attrs(description="Jahre", ordering="jahr_min")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@register_changelist(_models.Kalender, category=ModelType.ARCHIVGUT)
class KalenderList(SearchableListView):
    model = _models.Kalender
    list_display = ["titel", "zusammenfassung", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "spielort", "veranstaltung", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe", "spielort", "veranstaltung"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }

    @add_attrs(description="Jahre", ordering="jahr_min")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@register_changelist(_models.Foto, category=ModelType.ARCHIVGUT)
class FotoList(SearchableListView):
    model = _models.Foto
    ordering = ["titel", "datum"]
    list_display = ["titel", "foto_id", "size", "typ", "datum_localized", "schlagwort_list"]
    search_form_kwargs = {
        "fields": [
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
            "reihe",
            "datum__range",
        ],
        "labels": {"reihe": "Bildreihe"},
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
    }

    @add_attrs(description="Foto ID", ordering="id")
    def foto_id(self, obj: _models.Foto):
        """Return the id of the object, padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return str(obj.pk).zfill(6)

    @add_attrs(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Foto):
        return obj.datum.localize()

    @add_attrs(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_list(self, obj: _models.Foto):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()


@register_changelist(_models.Plattenfirma, category=ModelType.SONSTIGE)
class PlattenfirmaList(SearchableListView):
    model = _models.Plattenfirma
