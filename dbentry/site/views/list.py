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
        list_display = ["id", "name", "field_2"]


Use SearchableListView to add a search form to the changelist:

    @register_changelist(MyModel)
    class MyModelListView(SearchableListView):
        model = MyModel
        search_form_kwargs = {
            "fields": ["name", "field_2"]
        }
"""

import json
from urllib.parse import urljoin

from django.apps import apps
from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView

from dbentry import models as _models
from dbentry.export import resources
from dbentry.site.forms import MusikerSearchForm, null_boolean_select
from dbentry.site.registry import ModelType, register_changelist
from dbentry.site.templatetags.mizdb import add_preserved_filters
from dbentry.site.views.base import ORDER_VAR, BaseViewMixin, SearchableListView, ONLINE_HELP_INDEX
from dbentry.utils import add_attrs
from dbentry.utils.text import concat_limit
from dbentry.utils.url import get_change_url

# @formatter:off
# A green checkmark icon and a red X to use as representation of boolean values:
BOOLEAN_TRUE = mark_safe(
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-check text-success"><polyline points="20 6 9 17 4 12"></polyline></svg>'  # noqa
)
BOOLEAN_FALSE = mark_safe(
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-x text-danger"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>'  # noqa
)
# @formatter:on


def changelist_selection_sync(request):
    """
    A view called by the changelist selection script that returns a JsonResponse
    with ids of selected items that are not found in the database.
    The script will then remove these items from the selection.
    """
    model = apps.get_model(request.GET["model"])
    selection_ids = set(json.loads(request.GET.get("ids", [])))
    existing_ids = [str(pk) for pk in model.objects.filter(pk__in=selection_ids).values_list("pk", flat=True)]
    return JsonResponse({"remove": list(selection_ids.difference(existing_ids))})


def _get_continue_url(request, obj):
    """
    Return the URL to the change page of the given object. If the object is an
    Artikel instance, add changelist filters.
    """
    url = get_change_url(request, obj)
    if not url:  # pragma: no cover
        return ""
    if isinstance(obj, _models.Artikel):
        # Add useful changelist filters query parameters to the link URL
        filters = f"ausgabe__magazin={obj.ausgabe.magazin.pk}&ausgabe={obj.ausgabe.pk}"
        context = {"opts": obj._meta, "preserved_filters": urlencode({"_changelist_filters": filters})}
        url = add_preserved_filters(context=context, base_url=url)
    return url


@method_decorator(never_cache, name="dispatch")
class Index(BaseViewMixin, TemplateView):
    title = "Index"
    template_name = "mizdb/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add links that allow a user to continue editing the last 'Archivgut'
        # objects edited:
        def get_archivgut_content_types(site):
            """
            Return the content type objects of the models that are categorized
            as 'Archivgut' under the given site.
            """
            model_options = None
            for category, _model_options in site.model_list:
                if category == ModelType.ARCHIVGUT.value:
                    model_options = _model_options
                    break
            if model_options is None:  # pragma: no cover
                return None
            return [ContentType.objects.get_for_model(opts.model) for opts in model_options]

        logs = (
            LogEntry.objects.filter(
                user_id=self.request.user.pk, content_type__in=get_archivgut_content_types(self.site)
            )
            .exclude(action_flag=DELETION)
            .order_by("-action_time")
        )
        seen_objects = set()
        edits = []
        for log_entry in logs:
            try:
                obj = log_entry.get_edited_object()
            except ObjectDoesNotExist:
                # The object has since been deleted.
                continue
            if obj in seen_objects:
                continue

            edits.append((log_entry, f"{obj._meta.verbose_name}: {obj}", _get_continue_url(self.request, obj)))
            seen_objects.add(obj)
            if len(edits) == 5:
                break

        context["last_edits"] = edits
        return context


################################################################################
# ARCHIVGUT
################################################################################


@register_changelist(_models.Artikel, category=ModelType.ARCHIVGUT)
class ArtikelList(SearchableListView):
    model = _models.Artikel
    order_unfiltered_results = False
    prioritize_search_ordering = False
    list_display = [
        "id",
        "schlagzeile",
        "zusammenfassung_short",
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
        "tabular": ["ausgabe", "musiker", "band", "spielort", "veranstaltung"],
    }
    resource_class = resources.ArtikelResource

    @add_attrs(description="Zusammenfassung", ordering="zusammenfassung")
    def zusammenfassung_short(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)

    @add_attrs(description="Seite", ordering="seite")
    def seite_umfang(self, obj):
        return f"{obj.seite}{obj.seitenumfang}"

    @add_attrs(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_list(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    @add_attrs(description="Ausgabe", ordering="ausgabe___name")
    def ausgabe_name(self, obj: _models.Artikel) -> str:
        return obj.ausgabe._name

    @add_attrs(description="Magazin", ordering="ausgabe__magazin__magazin_name")
    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Audio, category=ModelType.ARCHIVGUT)
class AudioList(SearchableListView):
    model = _models.Audio
    ordering = ["titel", "jahr", "medium"]
    list_display = ["id", "titel", "jahr", "medium", "kuenstler_list", "plattennummer"]
    search_form_kwargs = {
        "fields": [
            "plattennummer__contains",  # also see AudioQuerySet.filter
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
    resource_class = resources.AudioResource

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Audio):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Ausgabe, category=ModelType.ARCHIVGUT)
class AusgabeList(SearchableListView):
    model = _models.Ausgabe
    ordering = ["magazin__magazin_name", "_name"]
    list_display = [
        "id",
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
    ]
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
        "widgets": {"sonderausgabe": null_boolean_select},
    }
    resource_class = resources.AusgabeResource
    sortable_by = [
        "ausgabe_name",
        "jahrgang",
        "magazin_name",
        "e_datum",
        "anz_artikel",
        "status",
    ]

    @add_attrs(description="Ausgabe", ordering="_name")
    def ausgabe_name(self, obj: _models.Ausgabe) -> str:
        return obj._name

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

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list

    @add_attrs(description="Magazin", ordering="magazin__magazin_name")
    def magazin_name(self, obj: _models.Ausgabe) -> str:
        return obj.magazin.magazin_name

    @add_attrs(description="Anz. Artikel", ordering="anz_artikel")
    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_artikel

    def get_queryset(self):
        """
        Apply chronological order to the result queryset unless an ordering is
        specified in the query string.
        """
        if ORDER_VAR in self.request.GET:
            return super().get_queryset()
        else:
            return super().get_queryset().chronological_order()


@register_changelist(_models.Brochure, category=ModelType.ARCHIVGUT)
class BrochureList(SearchableListView):
    model = _models.Brochure
    list_display = ["id", "titel", "zusammenfassung", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "schlagwort", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }
    resource_class = resources.BrochureResource
    help_url = urljoin(ONLINE_HELP_INDEX, "broschuere.html")
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "broschuere"})

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@register_changelist(_models.Buch, category=ModelType.ARCHIVGUT)
class BuchList(SearchableListView):
    model = _models.Buch
    ordering = ["titel"]
    list_display = ["id", "titel", "seitenumfang", "autoren_string", "kuenstler_list", "schlagwort_string"]
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
    resource_class = resources.BuchResource

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


@register_changelist(_models.Foto, category=ModelType.ARCHIVGUT)
class FotoList(SearchableListView):
    model = _models.Foto
    ordering = ["titel", "datum"]
    list_display = ["id", "titel", "foto_id", "size", "typ", "datum_localized", "schlagwort_list"]
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
    resource_class = resources.FotoResource

    @add_attrs(description="Foto ID", ordering="id")
    def foto_id(self, obj: _models.Foto):
        """Return the id of the object, padded with zeros."""
        if not obj.pk:  # pragma: no cover
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


@register_changelist(_models.Plakat, category=ModelType.ARCHIVGUT)
class PlakatList(SearchableListView):
    model = _models.Plakat
    ordering = ["titel", "datum"]
    list_display = ["id", "titel", "plakat_id", "size", "datum_localized", "veranstaltung_string"]
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
    resource_class = resources.PlakatResource

    @add_attrs(description="Plakat ID", ordering="id")
    def plakat_id(self, obj: _models.Plakat):
        """ID of this instance, with a prefixed 'P' and padded with zeros."""
        if not obj.pk:  # pragma: no cover
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


@register_changelist(_models.Kalender, category=ModelType.ARCHIVGUT)
class ProgrammheftList(SearchableListView):
    model = _models.Kalender
    list_display = ["id", "titel", "zusammenfassung", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "spielort", "veranstaltung", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe", "spielort", "veranstaltung"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }
    resource_class = resources.KalenderResource
    help_url = urljoin(ONLINE_HELP_INDEX, "programmheft.html")
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "programmheft"})

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@register_changelist(_models.Video, category=ModelType.ARCHIVGUT)
class VideoList(SearchableListView):
    model = _models.Video
    ordering = ["titel"]
    list_display = ["id", "titel", "medium", "kuenstler_list"]
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
    resource_class = resources.VideoResource

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Video):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.Katalog, category=ModelType.ARCHIVGUT)
class WarenkatalogList(SearchableListView):
    model = _models.Katalog
    list_display = ["id", "titel", "zusammenfassung", "art", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "jahre__jahr__range"],
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
        "filter_by": {"ausgabe": ("ausgabe__magazin", "magazin_id")},
    }
    resource_class = resources.KatalogResource
    help_url = urljoin(ONLINE_HELP_INDEX, "warenkatalog.html")
    offline_help_url = reverse_lazy("help", kwargs={"page_name": "warenkatalog"})

    @add_attrs(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.BaseBrochure):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


################################################################################
# STAMMDATEN
################################################################################


@register_changelist(_models.Autor, category=ModelType.STAMMDATEN)
class AutorList(SearchableListView):
    model = _models.Autor
    ordering = ["_name"]
    list_display = ["id", "autor_name", "person", "kuerzel", "magazin_string"]
    search_form_kwargs = {"fields": ["magazin", "person"]}
    resource_class = resources.AutorResource

    @add_attrs(description="Autor", ordering="_name")
    def autor_name(self, obj: _models.Autor):
        return obj._name

    @add_attrs(description="Magazin(e)", ordering="magazin_list")
    def magazin_string(self, obj: _models.Autor):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.magazin_list or self.get_empty_value_display()


@register_changelist(_models.Band, category=ModelType.STAMMDATEN)
class BandList(SearchableListView):
    model = _models.Band
    ordering = ["band_name"]
    list_display = ["id", "band_name", "genre_string", "musiker_string", "orte_string"]
    search_form_kwargs = {
        "fields": ["musiker", "genre", "orte__land", "orte"],
        "labels": {"musiker": "Mitglied"},
        "tabular": ["musiker"],
    }
    resource_class = resources.BandResource

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


@register_changelist(_models.Genre, category=ModelType.STAMMDATEN)
class GenreList(SearchableListView):
    model = _models.Genre
    list_display = ["id", "genre", "alias_string"]
    resource_class = resources.GenreResource

    @add_attrs(description="Aliase")
    def alias_string(self, obj: _models.Genre):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()


@register_changelist(_models.Magazin, category=ModelType.STAMMDATEN)
class MagazinList(SearchableListView):
    model = _models.Magazin
    ordering = ["magazin_name"]
    list_display = ["id", "magazin_name", "short_beschreibung", "orte_string", "anz_ausgaben"]
    search_form_kwargs = {
        "fields": ["verlag", "herausgeber", "orte", "genre", "issn", "fanzine"],
        "widgets": {"fanzine": null_boolean_select},
    }
    resource_class = resources.MagazinResource

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


@register_changelist(_models.Musiker, category=ModelType.STAMMDATEN)
class MusikerList(SearchableListView):
    model = _models.Musiker
    ordering = ["kuenstler_name"]
    list_display = ["id", "kuenstler_name", "genre_string", "band_string", "orte_string"]
    search_form_kwargs = {
        "fields": ["band", "person", "genre", "instrument", "orte__land", "orte"],
        "form": MusikerSearchForm,
    }
    resource_class = resources.MusikerResource

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


@register_changelist(_models.Ort, category=ModelType.STAMMDATEN)
class OrtList(SearchableListView):
    model = _models.Ort
    ordering = ["land", "bland", "stadt"]
    list_display = ["id", "stadt", "bland", "land"]
    list_display_links = ["stadt", "bland", "land"]
    search_form_kwargs = {
        "fields": ["land", "bland"],
        "filter_by": {"bland": ("land", "land_id")},
    }
    resource_class = resources.OrtResource


@register_changelist(_models.Person, category=ModelType.STAMMDATEN)
class PersonList(SearchableListView):
    model = _models.Person
    ordering = ["nachname", "vorname"]
    list_display = ["id", "vorname", "nachname", "orte_string", "is_musiker", "is_autor"]
    list_display_links = ["vorname", "nachname"]
    search_form_kwargs = {
        "fields": ["orte", "orte__land", "orte__bland", "gnd_id"],
        "filter_by": {"orte__bland": ("orte__land", "land_id")},
    }
    resource_class = resources.PersonResource

    @add_attrs(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Person):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()

    @add_attrs(description="Ist Musiker", boolean=True)
    def is_musiker(self, obj: _models.Person):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        if obj.is_musiker:
            return BOOLEAN_TRUE
        return BOOLEAN_FALSE

    @add_attrs(description="Ist Autor", boolean=True)
    def is_autor(self, obj: _models.Person):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        if obj.is_autor:
            return BOOLEAN_TRUE
        return BOOLEAN_FALSE


@register_changelist(_models.Schlagwort, category=ModelType.STAMMDATEN)
class SchlagwortList(SearchableListView):
    model = _models.Schlagwort
    ordering = ["schlagwort"]
    list_display = ["id", "schlagwort", "alias_string"]
    resource_class = resources.SchlagwortResource

    @add_attrs(description="Aliase", ordering="alias_list")
    def alias_string(self, obj: _models.Schlagwort):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()


################################################################################
# SONSTIGE
################################################################################


@register_changelist(_models.Herausgeber, category=ModelType.SONSTIGE)
class HerausgeberList(SearchableListView):
    model = _models.Herausgeber
    ordering = ["herausgeber"]
    list_display = ["id", "herausgeber"]
    resource_class = resources.HerausgeberResource


@register_changelist(_models.Instrument, category=ModelType.SONSTIGE)
class InstrumentList(SearchableListView):
    model = _models.Instrument
    ordering = ["instrument"]
    list_display = ["id", "instrument", "kuerzel"]
    resource_class = resources.InstrumentResource


@register_changelist(_models.Plattenfirma, category=ModelType.SONSTIGE)
class PlattenfirmaList(SearchableListView):
    model = _models.Plattenfirma
    list_display = ["id", "name"]
    resource_class = resources.PlattenfirmaResource
    view_has_help_page = False


@register_changelist(_models.Spielort, category=ModelType.SONSTIGE)
class SpielortList(SearchableListView):
    model = _models.Spielort
    ordering = ["name", "ort"]
    list_display = ["id", "name", "ort"]
    search_form_kwargs = {"fields": ["ort", "ort__land"]}
    resource_class = resources.SpielortResource


@register_changelist(_models.Veranstaltung, category=ModelType.SONSTIGE)
class VeranstaltungList(SearchableListView):
    model = _models.Veranstaltung
    ordering = ["name", "spielort", "datum"]
    list_display = ["id", "name", "datum_localized", "spielort", "kuenstler_list"]
    search_form_kwargs = {
        "fields": ["musiker", "band", "schlagwort", "genre", "person", "spielort", "reihe", "datum__range"],
        "tabular": ["musiker", "band", "spielort"],
    }
    resource_class = resources.VeranstaltungResource

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
    list_display = ["id", "verlag_name", "sitz"]
    search_form_kwargs = {
        "fields": ["sitz", "sitz__land", "sitz__bland"],
        "labels": {"sitz": "Sitz"},
        "filter_by": {"sitz__bland": ("sitz__land", "land_id")},
    }
    resource_class = resources.VerlagResource


@register_changelist(_models.Lagerort, category=ModelType.SONSTIGE)
class LagerortList(SearchableListView):
    model = _models.Lagerort
    list_display = ["id", "ort", "raum", "regal", "fach", "ordner"]
    resource_class = resources.LagerortResource


@register_changelist(_models.Geber, category=ModelType.SONSTIGE)
class GeberList(SearchableListView):
    model = _models.Geber
    list_display = ["id", "name"]
    resource_class = resources.GeberResource
    view_has_help_page = False


@register_changelist(_models.Provenienz, category=ModelType.SONSTIGE)
class ProvenienzList(SearchableListView):
    model = _models.Provenienz
    list_display = ["id", "geber", "typ"]
    resource_class = resources.ProvenienzResource


@register_changelist(_models.Schriftenreihe, category=ModelType.SONSTIGE)
class SchriftenreiheList(SearchableListView):
    model = _models.Schriftenreihe
    list_display = ["id", "name"]
    resource_class = resources.SchriftenreiheResource
    view_has_help_page = False


@register_changelist(_models.Bildreihe, category=ModelType.SONSTIGE)
class BildreiheList(SearchableListView):
    model = _models.Bildreihe
    list_display = ["id", "name"]
    resource_class = resources.BildreiheResource
    view_has_help_page = False


@register_changelist(_models.Veranstaltungsreihe, category=ModelType.SONSTIGE)
class VeranstaltungsreiheList(SearchableListView):
    model = _models.Veranstaltungsreihe
    list_display = ["id", "name"]
    resource_class = resources.VeranstaltungsreiheResource
    view_has_help_page = False


@register_changelist(_models.VideoMedium, category=ModelType.SONSTIGE)
class VideoMediumList(SearchableListView):
    model = _models.VideoMedium
    list_display = ["id", "medium"]
    resource_class = resources.VideoMediumResource
    view_has_help_page = False


@register_changelist(_models.AudioMedium, category=ModelType.SONSTIGE)
class AudioMediumList(SearchableListView):
    model = _models.AudioMedium
    list_display = ["id", "medium"]
    resource_class = resources.AudioMediumResource
    view_has_help_page = False


@register_changelist(_models.Bestand, category=ModelType.SONSTIGE)
class BestandList(SearchableListView):
    model = _models.Bestand
    list_display = ["signatur", "lagerort", "provenienz", "anmerkungen", "bestand_object_string"]
    search_form_kwargs = {"fields": ["lagerort", "provenienz", "signatur"]}
    resource_class = resources.BestandResource
    include_add_btn = False

    @add_attrs(description="Archivgut")
    def bestand_object_string(self, obj):
        """
        Return a text representation of the archive object that the given
        Bestand object refers to.
        """
        if bestand_object := obj.bestand_object:
            return f"{bestand_object._meta.verbose_name}: {bestand_object}"


@register_changelist(_models.Memorabilien, category=ModelType.ARCHIVGUT)
class MemorabilienList(SearchableListView):
    model = _models.Memorabilien
    list_display = ["id", "titel", "typ", "short_beschreibung", "kuenstler_list"]
    search_form_kwargs = {
        "fields": [
            "typ",
            "musiker",
            "band",
            "schlagwort",
            "genre",
            "ort",
            "spielort",
            "veranstaltung",
            "person",
        ],
        "tabular": ["musiker", "band", "spielort", "veranstaltung"],
    }
    resource_class = resources.MemorabilienResource
    view_has_help_page = True

    @add_attrs(description="Beschreibung", ordering="beschreibung")
    def short_beschreibung(self, obj: _models.Memorabilien):
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")

    @add_attrs(description="Künstler")
    def kuenstler_list(self, obj: _models.Memorabilien):
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@register_changelist(_models.MemoTyp, category=ModelType.SONSTIGE)
class MemoTypList(SearchableListView):
    model = _models.MemoTyp
    list_display = ["id", "name"]
    resource_class = resources.MemoTypResource
    view_has_help_page = False
