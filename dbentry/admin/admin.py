from datetime import datetime, timedelta
from typing import Any, List, Optional, Type, Union

# noinspection PyPackageRequirements
from dal import autocomplete
from django.contrib import admin
from django.contrib.admin.decorators import action, display
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_permission_codename
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission, User
from django.db import transaction
from django.db.models import Count, IntegerField, ManyToManyField, Min, OuterRef, QuerySet, Subquery, Value
from django.db.models import Field as ModelField
from django.db.models.functions import Coalesce
from django.forms import BaseInlineFormSet, ChoiceField, ModelForm
from django.http import HttpRequest
from django.utils.safestring import SafeText
from django_admin_logs.admin import LogEntryAdmin
from mizdb_watchlist.admin import WatchlistAdmin
from mizdb_watchlist.models import Watchlist

import dbentry.admin.actions as _actions
import dbentry.forms as _forms
import dbentry.m2m as _m2m
import dbentry.models as _models
from dbentry.admin.autocomplete.widgets import make_widget
from dbentry.admin.base import (
    BaseAliasInline,
    BaseAusgabeInline,
    BaseGenreInline,
    BaseOrtInLine,
    BaseSchlagwortInline,
    BaseStackedInline,
    BaseTabularInline,
    MIZModelAdmin,
)
from dbentry.admin.changelist import AusgabeChangeList, BestandChangeList
from dbentry.admin.site import miz_site
from dbentry.export import resources
from dbentry.search.mixins import MIZAdminSearchFormMixin
from dbentry.utils.admin import log_change
from dbentry.utils.copyrelated import copy_related_set
from dbentry.utils.html import get_obj_link
from dbentry.utils.text import concat_limit

# FIXME: deleting a related m2m object and then saving the parent form results
#  in a form error since the select for that relation still references the
#  deleted object (via the id)
# 1. create artikel
# 2. add band
# 3. save artikel
# 4. delete band
# 5. save artikel -> errors


class BestandInLine(BaseTabularInline):
    model = _models.Bestand
    form = _forms.BestandInlineForm
    fields = ["bestand_signatur", "lagerort", "provenienz", "anmerkungen"]
    readonly_fields = ["bestand_signatur"]

    # 'copylast' class allows inlines.js to copy the last selected bestand to a
    # new row.
    classes = ["copylast"]

    # noinspection PyUnresolvedReferences
    verbose_name = _models.Bestand._meta.verbose_name
    # noinspection PyUnresolvedReferences
    verbose_name_plural = _models.Bestand._meta.verbose_name_plural

    @display(description="Signatur")
    def bestand_signatur(self, obj: _models.Bestand) -> str:
        """Display the signatur of this Bestand object."""
        return str(obj.signatur) or ""


@admin.register(_models.Audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Audio.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Audio.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Audio.person.through
        verbose_model = _models.Person

    class MusikerInLine(BaseStackedInline):
        model = _models.Audio.musiker.through
        extra = 0
        filter_horizontal = ["instrument"]
        verbose_model = _models.Musiker
        # fmt: off
        fieldsets = [
            (None, {"fields": ["musiker"]}),
            ("Instrumente", {"fields": ["instrument"], "classes": ["collapse", "collapsed"]}),
        ]
        # fmt: on
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Audio.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class SpielortInLine(BaseTabularInline):
        model = _models.Audio.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Audio.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    class OrtInLine(BaseTabularInline):
        model = _models.Audio.ort.through
        verbose_model = _models.Ort

    class PlattenInLine(BaseTabularInline):
        model = _models.Audio.plattenfirma.through
        verbose_model = _models.Plattenfirma

    class AusgabeInLine(BaseAusgabeInline):
        model = _models.Ausgabe.audio.through
        # Note that the tabular autocomplete widget for 'ausgabe' is created
        # by the AusgabeMagazinFieldForm of this inline class.

    class DateiInLine(BaseTabularInline):
        model = _m2m.m2m_datei_quelle
        fields = ["datei"]
        verbose_model = _models.Datei

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    collapse_all = True
    form = _forms.AudioForm
    index_category = "Archivgut"
    save_on_top = True
    list_display = ["titel", "jahr", "medium", "kuenstler_list"]
    list_select_related = ["medium"]
    ordering = ["titel", "jahr", "medium"]

    # fmt: off
    fieldsets = [
        (None, {
            "fields": [
                "titel", "tracks", "laufzeit", "jahr", "land_pressung", "original", "quelle",
                ("medium", "medium_qty"), "plattennummer", "beschreibung", "bemerkungen"
            ]
        }),
        ("Discogs", {
            "fields": ["release_id", "discogs_url"],
            "classes": ["collapse", "collapsed"]
        }),
    ]
    # fmt: on
    inlines = [
        MusikerInLine,
        BandInLine,
        SchlagwortInLine,
        GenreInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
        PlattenInLine,
        AusgabeInLine,
        DateiInLine,
        BestandInLine,
    ]
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
    resource_class = resources.AudioResource

    @display(description="Künstler")
    def kuenstler_list(self, obj: _models.Audio) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@admin.register(_models.Ausgabe, site=miz_site)
class AusgabenAdmin(MIZModelAdmin):
    class NumInLine(BaseTabularInline):
        model = _models.AusgabeNum
        extra = 0

    class MonatInLine(BaseTabularInline):
        model = _models.AusgabeMonat
        verbose_model = _models.Monat
        extra = 0

    class LNumInLine(BaseTabularInline):
        model = _models.AusgabeLnum
        extra = 0

    class JahrInLine(BaseTabularInline):
        model = _models.AusgabeJahr
        extra = 0
        verbose_name_plural = "erschienen im Jahr"

    class AudioInLine(BaseTabularInline):
        model = _models.Ausgabe.audio.through
        verbose_model = _models.Audio

    class VideoInLine(BaseTabularInline):
        model = _models.Ausgabe.video.through
        verbose_model = _models.Video

    index_category = "Archivgut"
    inlines = [NumInLine, MonatInLine, LNumInLine, JahrInLine, AudioInLine, VideoInLine, BestandInLine]
    ordering = ["magazin__magazin_name", "_name"]
    list_select_related = ["magazin"]
    require_confirmation = True
    confirmation_threshold = 0.8

    fields = ["magazin", ("status", "sonderausgabe"), "e_datum", "jahrgang", "beschreibung", "bemerkungen"]
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

    actions = [
        _actions.merge_records,
        _actions.bulk_jg,
        _actions.change_bestand,
        _actions.moveto_brochure,
        "change_status_unbearbeitet",
        "change_status_inbearbeitung",
        "change_status_abgeschlossen",
        _actions.summarize,
    ]
    resource_class = resources.AusgabeResource

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> Type[AusgabeChangeList]:
        return AusgabeChangeList

    @display(description="Ausgabe", ordering="_name")
    def ausgabe_name(self, obj: _models.Ausgabe) -> str:
        return obj._name

    @display(description="Magazin", ordering="magazin__magazin_name")
    def magazin_name(self, obj: _models.Ausgabe) -> str:
        return obj.magazin.magazin_name

    @display(description="Anz. Artikel", ordering="anz_artikel")
    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_artikel

    @display(description="Jahre", ordering="jahr_list")
    def jahr_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list

    @display(description="Nummer", ordering="num_list")
    def num_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.num_list

    @display(description="lfd. Nummer", ordering="lnum_list")
    def lnum_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.lnum_list

    @display(description="Monate")
    def monat_list(self, obj: _models.Ausgabe) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.monat_list

    def _change_status(self, request: HttpRequest, queryset: QuerySet, status: str) -> None:
        """Update the ``status`` of the Ausgabe instances in ``queryset``."""
        with transaction.atomic():
            # Remove ordering, as queryset ordering may depend on annotations
            # which would be removed before the update.
            # See: https://code.djangoproject.com/ticket/28897
            queryset.order_by().update(status=status, _changed_flag=False)
        try:
            with transaction.atomic():
                for obj in queryset:
                    # noinspection PyUnresolvedReferences
                    log_change(request.user.pk, obj, fields=["status"])
        except Exception as e:
            message_text = f"Fehler beim Erstellen der LogEntry Objekte: \n{e.__class__.__name__}: {e.args[0]!s}"
            self.message_user(request, message_text, "ERROR")

    @action(permissions=["change"], description="Status ändern: unbearbeitet")
    def change_status_unbearbeitet(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        UNBEARBEITET.
        """
        self._change_status(request, queryset, str(_models.Ausgabe.Status.UNBEARBEITET))

    @action(permissions=["change"], description="Status ändern: in Bearbeitung")
    def change_status_inbearbeitung(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        INBEARBEITUNG.
        """
        self._change_status(request, queryset, str(_models.Ausgabe.Status.INBEARBEITUNG))

    @action(permissions=["change"], description="Status ändern: abgeschlossen")
    def change_status_abgeschlossen(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        ABGESCHLOSSEN.
        """
        self._change_status(request, queryset, str(_models.Ausgabe.Status.ABGESCHLOSSEN))

    @staticmethod
    def has_moveto_brochure_permission(request: HttpRequest) -> bool:
        """
        Check that the request's user has permission to add Brochure objects
        and permission to delete Ausgabe objects.
        """
        # Called when checking permissions for the 'moveto_brochure' action by:
        # django.contrib.admin.checks.ModelAdminChecks._check_action_permission_methods
        perms = [
            "%s.%s" % (opts.app_label, get_permission_codename(name, opts))
            for name, opts in [("delete", _models.Ausgabe._meta), ("add", _models.BaseBrochure._meta)]
        ]
        # noinspection PyUnresolvedReferences
        return request.user.has_perms(perms)

    def _get_changelist_link_relations(self) -> list:
        return [
            (_models.Artikel, "ausgabe", "Artikel"),
            (_models.Brochure, "ausgabe", "Broschüren"),
            (_models.Kalender, "ausgabe", "Programmhefte"),
            (_models.Katalog, "ausgabe", "Warenkataloge"),
        ]


@admin.register(_models.Autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = _models.Autor.magazin.through
        verbose_model = _models.Magazin
        extra = 1

    class URLInLine(BaseTabularInline):
        model = _models.AutorURL

    actions = [_actions.merge_records, _actions.summarize]
    form = _forms.AutorForm
    index_category = "Stammdaten"
    inlines = [URLInLine, MagazinInLine]
    list_display = ["autor_name", "person", "kuerzel", "magazin_string"]
    list_select_related = ["person"]
    search_form_kwargs = {"fields": ["magazin", "person"]}
    ordering = ["_name"]
    require_confirmation = True
    resource_class = resources.AutorResource

    @display(description="Autor", ordering="_name")
    def autor_name(self, obj: _models.Autor) -> str:
        return obj._name

    @display(description="Magazin(e)", ordering="magazin_list")
    def magazin_string(self, obj: _models.Autor) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.magazin_list or self.get_empty_value_display()


@admin.register(_models.Artikel, site=miz_site)
class ArtikelAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Artikel.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Artikel.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Artikel.person.through
        verbose_model = _models.Person

    class AutorInLine(BaseTabularInline):
        model = _models.Artikel.autor.through
        verbose_model = _models.Autor

    class MusikerInLine(BaseTabularInline):
        model = _models.Artikel.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Artikel.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Artikel.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Artikel.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["spielort"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Artikel.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    actions = [_actions.merge_records, _actions.summarize]
    form = _forms.ArtikelForm
    index_category = "Archivgut"
    save_on_top = True
    list_select_related = ["ausgabe", "ausgabe__magazin"]
    ordering = ["ausgabe__magazin__magazin_name", "ausgabe___name", "seite", "schlagzeile"]

    fields = [
        ("ausgabe__magazin", "ausgabe"),
        "schlagzeile",
        ("seite", "seitenumfang"),
        "zusammenfassung",
        "beschreibung",
        "bemerkungen",
    ]
    inlines = [
        AutorInLine,
        MusikerInLine,
        BandInLine,
        SchlagwortInLine,
        GenreInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
    ]
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
        "forwards": {"ausgabe": "ausgabe__magazin"},
        "tabular": ["ausgabe", "musiker", "band", "spielort", "veranstaltung"],
    }
    resource_class = resources.ArtikelResource

    @display(description="Ausgabe", ordering="ausgabe___name")
    def ausgabe_name(self, obj: _models.Artikel) -> str:
        return obj.ausgabe._name

    @display(description="Zusammenfassung", ordering="zusammenfassung")
    def zusammenfassung_string(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)

    @display(description="Magazin", ordering="ausgabe__magazin__magazin_name")
    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name

    @display(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_string(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    @display(description="Künstler")
    def kuenstler_list(self, obj: _models.Artikel) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@admin.register(_models.Band, site=miz_site)
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Band.genre.through

    class MusikerInLine(BaseTabularInline):
        model = _models.Band.musiker.through
        verbose_name = "Band-Mitglied"
        verbose_name_plural = "Band-Mitglieder"
        tabular_autocomplete = ["musiker"]

    class AliasInLine(BaseAliasInline):
        model = _models.BandAlias

    class OrtInLine(BaseOrtInLine):
        model = _models.Band.orte.through

    class URLInLine(BaseTabularInline):
        model = _models.BandURL

    actions = [_actions.merge_records, _actions.summarize]
    form = _forms.BandForm
    index_category = "Stammdaten"
    inlines = [URLInLine, GenreInLine, AliasInLine, MusikerInLine, OrtInLine]
    list_display = ["band_name", "genre_string", "musiker_string", "orte_string"]
    save_on_top = True
    ordering = ["band_name"]
    require_confirmation = True

    search_form_kwargs = {
        "fields": ["musiker", "genre", "orte__land", "orte"],
        "labels": {"musiker": "Mitglied"},
        "tabular": ["musiker"],
    }
    resource_class = resources.BandResource

    @display(description="Genres", ordering="genre_list")
    def genre_string(self, obj: _models.Band) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.genre_list or self.get_empty_value_display()

    @display(description="Mitglieder", ordering="musiker_list")
    def musiker_string(self, obj: _models.Band) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.musiker_list or self.get_empty_value_display()

    @display(description="Aliase", ordering="alias_list")
    def alias_string(self, obj: _models.Band) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()

    @display(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Band) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()


@admin.register(_models.Plakat, site=miz_site)
class PlakatAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Plakat.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Plakat.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Plakat.person.through
        verbose_model = _models.Person

    class MusikerInLine(BaseTabularInline):
        model = _models.Plakat.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Plakat.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Plakat.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Plakat.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Plakat.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    collapse_all = True
    form = _forms.PlakatForm
    index_category = "Archivgut"
    list_display = ["titel", "plakat_id", "size", "datum_localized", "veranstaltung_string"]
    readonly_fields = ["plakat_id"]
    save_on_top = True
    ordering = ["titel", "datum"]
    fields = ["titel", "plakat_id", "size", "datum", "reihe", "copy_related", "beschreibung", "bemerkungen"]

    inlines = [
        SchlagwortInLine,
        GenreInLine,
        MusikerInLine,
        BandInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
        BestandInLine,
    ]
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

    @display(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Plakat) -> str:
        return obj.datum.localize()

    @display(description="Veranstaltungen", ordering="veranstaltung_list")
    def veranstaltung_string(self, obj: _models.Plakat) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.veranstaltung_list or self.get_empty_value_display()

    def get_fields(self, request: HttpRequest, obj: Optional[_models.Plakat] = None) -> List[str]:
        """
        Remove the 'copy_related' formfield, if the user does not have change
        permissions on the object.
        """
        fields = super().get_fields(request, obj)
        if not self.has_change_permission(request, obj):
            return [f for f in fields if f != "copy_related"]
        return fields

    def save_related(
        self, request: HttpRequest, form: ModelForm, formsets: List[BaseInlineFormSet], change: bool
    ) -> None:
        super().save_related(request, form, formsets, change)
        self._copy_related(request, form.instance)

    @staticmethod
    def _copy_related(request: HttpRequest, obj: _models.Plakat) -> None:
        """Copy Band and Musiker instances of Veranstaltung to this object."""
        if "copy_related" in request.POST:
            copy_related_set(request, obj, "veranstaltung__band", "veranstaltung__musiker")

    @display(description="Plakat ID", ordering="id")
    def plakat_id(self, obj: _models.Plakat) -> str:
        """ID of this instance, with a prefixed 'P' and padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return "P" + str(obj.pk).zfill(6)


@admin.register(_models.Buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Buch.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Buch.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Buch.person.through
        verbose_model = _models.Person

    class AutorInLine(BaseTabularInline):
        model = _models.Buch.autor.through
        verbose_model = _models.Autor

    class MusikerInLine(BaseTabularInline):
        model = _models.Buch.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Buch.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Buch.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Buch.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Buch.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    class HerausgeberInLine(BaseTabularInline):
        model = _models.Buch.herausgeber.through
        verbose_model = _models.Herausgeber

    class VerlagInLine(BaseTabularInline):
        model = _models.Buch.verlag.through
        verbose_model = _models.Verlag

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    collapse_all = True
    changelist_link_labels = {"buch": "Aufsätze"}
    form = _forms.BuchForm
    index_category = "Archivgut"
    save_on_top = True
    ordering = ["titel"]

    # fmt: off
    fieldsets = [
        (None, {
            "fields": [
                "titel", "seitenumfang", "jahr", "auflage", "schriftenreihe",
                ("buchband", "is_buchband"), "ISBN", "EAN", "sprache",
                "beschreibung", "bemerkungen"
            ]
        }),
        ("Original Angaben (bei Übersetzung)", {
            "fields": ["titel_orig", "jahr_orig"],
            "description": "Angaben zum Original eines übersetzten Buches.",
            "classes": ["collapse", "collapsed"],
        }),
    ]
    # fmt: on
    inlines = [
        AutorInLine,
        MusikerInLine,
        BandInLine,
        SchlagwortInLine,
        GenreInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
        HerausgeberInLine,
        VerlagInLine,
        BestandInLine,
    ]
    list_display = ["titel", "seitenumfang", "autoren_string", "kuenstler_list", "schlagwort_string"]
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
        # 'autor' help_text refers to quick item creation which is not allowed
        # in search forms - disable the help_text.
        "help_texts": {"autor": None},
    }
    resource_class = resources.BuchResource

    @display(description="Autoren", ordering="autor_list")
    def autoren_string(self, obj: _models.Buch) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.autor_list or self.get_empty_value_display()

    @display(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_string(self, obj: _models.Buch) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()

    @display(description="Künstler")
    def kuenstler_list(self, obj: _models.Buch) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@admin.register(_models.Dokument, site=miz_site)
class DokumentAdmin(MIZModelAdmin):
    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    index_category = "Archivgut"
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ["titel"]


@admin.register(_models.Genre, site=miz_site)
class GenreAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.GenreAlias

    actions = [_actions.merge_records, _actions.replace]
    index_category = "Stammdaten"
    inlines = [AliasInLine]
    list_display = ["genre", "alias_string"]
    ordering = ["genre"]
    # Need to define search_fields to have the template render the default
    # search bar. Note that the fields declared here do not matter, as the
    # search will be a postgres text search on the model's SearchVectorField.
    search_fields = ["__ANY__"]
    require_confirmation = True
    resource_class = resources.GenreResource

    @display(description="Aliase")
    def alias_string(self, obj: _models.Genre) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()

    def _get_changelist_link_relations(self) -> list:
        return [
            (_models.Musiker, "genre", None),
            (_models.Band, "genre", None),
            (_models.Magazin, "genre", None),
            (_models.Artikel, "genre", None),
            (_models.Buch, "genre", None),
            (_models.Audio, "genre", None),
            (_models.Plakat, "genre", None),
            (_models.Dokument, "genre", None),
            (_models.Memorabilien, "genre", None),
            (_models.Technik, "genre", None),
            (_models.Veranstaltung, "genre", None),
            (_models.Video, "genre", None),
            (_models.Datei, "genre", None),
            (_models.Brochure, "genre", None),
            (_models.Kalender, "genre", None),
            (_models.Katalog, "genre", None),
            (_models.Foto, "genre", None),
        ]


@admin.register(_models.Magazin, site=miz_site)
class MagazinAdmin(MIZModelAdmin):
    class URLInLine(BaseTabularInline):
        model = _models.MagazinURL

    class VerlagInLine(BaseTabularInline):
        model = _models.Magazin.verlag.through
        verbose_model = _models.Verlag

    class HerausgeberInLine(BaseTabularInline):
        model = _models.Magazin.herausgeber.through
        verbose_model = _models.Herausgeber

    class GenreInLine(BaseGenreInline):
        model = _models.Magazin.genre.through

    class OrtInLine(BaseOrtInLine):
        model = _models.Magazin.orte.through

    actions = [_actions.merge_records, _actions.summarize]
    index_category = "Stammdaten"
    inlines = [URLInLine, GenreInLine, VerlagInLine, HerausgeberInLine, OrtInLine]
    list_display = ["magazin_name", "short_beschreibung", "orte_string", "anz_ausgaben"]
    ordering = ["magazin_name"]
    require_confirmation = True

    search_form_kwargs = {
        "fields": ["verlag", "herausgeber", "orte", "genre", "issn", "fanzine"],
    }
    resource_class = resources.MagazinResource

    @display(description="Anz. Ausgaben", ordering="anz_ausgaben")
    def anz_ausgaben(self, obj: _models.Magazin) -> int:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.anz_ausgaben

    @display(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Magazin) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()

    @display(description="Beschreibung", ordering="beschreibung")
    def short_beschreibung(self, obj: _models.Magazin) -> str:
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")

    def get_exclude(self, request: HttpRequest, obj: Optional[_models.Magazin] = None) -> List[str]:
        """
        Exclude 'ausgaben_merkmal' from the add/change page if the current
        user is not a superuser.
        """
        exclude = super().get_exclude(request, obj) or []
        # noinspection PyUnresolvedReferences
        if not request.user.is_superuser:
            exclude = list(exclude)  # Copy the iterable.
            exclude.append("ausgaben_merkmal")
        return exclude


@admin.register(_models.Memorabilien, site=miz_site)
class MemoAdmin(MIZModelAdmin):
    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    index_category = "Archivgut"
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ["titel"]


@admin.register(_models.Musiker, site=miz_site)
class MusikerAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Musiker.genre.through

    class BandInLine(BaseTabularInline):
        model = _models.Band.musiker.through
        verbose_name_plural = "Ist Mitglied in"
        verbose_name = "Band"
        tabular_autocomplete = ["band"]

    class AliasInLine(BaseAliasInline):
        model = _models.MusikerAlias

    class InstrInLine(BaseTabularInline):
        model = _models.Musiker.instrument.through
        verbose_name_plural = "Spielt Instrument"
        verbose_name = "Instrument"

    class OrtInLine(BaseOrtInLine):
        model = _models.Musiker.orte.through

    class URLInLine(BaseTabularInline):
        model = _models.MusikerURL

    actions = [_actions.merge_records, _actions.summarize]
    form = _forms.MusikerForm
    fields = ["kuenstler_name", "person", "beschreibung", "bemerkungen"]
    index_category = "Stammdaten"
    inlines = [URLInLine, GenreInLine, AliasInLine, BandInLine, OrtInLine, InstrInLine]
    list_display = ["kuenstler_name", "genre_string", "band_string", "orte_string"]
    save_on_top = True
    search_form_kwargs = {"fields": ["person", "genre", "instrument", "orte__land", "orte"]}
    ordering = ["kuenstler_name"]
    require_confirmation = True
    resource_class = resources.MusikerResource

    @display(description="Bands", ordering="band_list")
    def band_string(self, obj: _models.Musiker) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.band_list or self.get_empty_value_display()

    @display(description="Genres", ordering="genre_list")
    def genre_string(self, obj: _models.Musiker) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.genre_list or self.get_empty_value_display()

    @display(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Musiker) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()


@admin.register(_models.Person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = _models.Person.orte.through

    class URLInLine(BaseTabularInline):
        model = _models.PersonURL

    actions = [_actions.merge_records, _actions.summarize]
    index_category = "Stammdaten"
    inlines = [URLInLine, OrtInLine]
    list_display = ("vorname", "nachname", "orte_string", "is_musiker", "is_autor")
    list_display_links = ["vorname", "nachname"]
    ordering = ["nachname", "vorname"]
    form = _forms.PersonForm
    require_confirmation = True

    # fmt: off
    fieldsets = [
        (None, {
            "fields": ["vorname", "nachname", "beschreibung", "bemerkungen"],
        }),
        ("Gemeinsame Normdatei", {
            "fields": ["gnd_id", "gnd_name", "dnb_url"],
            "classes": ["collapse", "collapsed"],
        })
    ]
    # fmt: on

    search_form_kwargs = {
        "fields": ["orte", "orte__land", "orte__bland", "gnd_id"],
        "forwards": {"orte__bland": "orte__land"},
    }
    resource_class = resources.PersonResource

    @display(description="Ist Musiker", boolean=True)
    def is_musiker(self, obj: _models.Person) -> bool:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.is_musiker

    @display(description="Ist Autor", boolean=True)
    def is_autor(self, obj: _models.Person) -> bool:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.is_autor

    @display(description="Orte", ordering="orte_list")
    def orte_string(self, obj: _models.Person) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.orte_list or self.get_empty_value_display()


@admin.register(_models.Schlagwort, site=miz_site)
class SchlagwortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SchlagwortAlias
        extra = 1

    actions = [_actions.merge_records, _actions.replace]
    index_category = "Stammdaten"
    inlines = [AliasInLine]
    list_display = ["schlagwort", "alias_string"]
    ordering = ["schlagwort"]
    # Need to define search_fields to have the template render the default
    # search bar. Note that the fields declared here do not matter, as the
    # search will be a postgres text search on the model's SearchVectorField.
    search_fields = ["__ANY__"]
    require_confirmation = True
    resource_class = resources.SchlagwortResource

    @display(description="Aliase", ordering="alias_list")
    def alias_string(self, obj: _models.Schlagwort) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.alias_list or self.get_empty_value_display()


@admin.register(_models.Spielort, site=miz_site)
class SpielortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SpielortAlias

    class URLInLine(BaseTabularInline):
        model = _models.SpielortURL

    list_display = ["name", "ort"]
    inlines = [URLInLine, AliasInLine]
    search_form_kwargs = {"fields": ["ort", "ort__land"]}
    ordering = ["name", "ort"]
    list_select_related = ["ort"]
    require_confirmation = True
    resource_class = resources.SpielortResource


@admin.register(_models.Technik, site=miz_site)
class TechnikAdmin(MIZModelAdmin):
    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    index_category = "Archivgut"
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ["titel"]


@admin.register(_models.Veranstaltung, site=miz_site)
class VeranstaltungAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Veranstaltung.genre.through

    class BandInLine(BaseTabularInline):
        model = _models.Veranstaltung.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class PersonInLine(BaseTabularInline):
        model = _models.Veranstaltung.person.through
        verbose_model = _models.Person

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Veranstaltung.schlagwort.through

    class MusikerInLine(BaseTabularInline):
        model = _models.Veranstaltung.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ["musiker"]

    class AliasInLine(BaseAliasInline):
        model = _models.VeranstaltungAlias

    class URLInLine(BaseTabularInline):
        model = _models.VeranstaltungURL

    collapse_all = True
    inlines = [URLInLine, AliasInLine, MusikerInLine, BandInLine, SchlagwortInLine, GenreInLine, PersonInLine]
    list_display = ["name", "datum_localized", "spielort", "kuenstler_list"]
    save_on_top = True
    ordering = ["name", "spielort", "datum"]
    tabular_autocomplete = ["spielort"]
    search_form_kwargs = {
        "fields": ["musiker", "band", "schlagwort", "genre", "person", "spielort", "reihe", "datum__range"],
        "tabular": ["musiker", "band"],
    }
    require_confirmation = True
    resource_class = resources.VeranstaltungResource

    @display(description="Künstler")
    def kuenstler_list(self, obj: _models.Veranstaltung) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()

    @display(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Veranstaltung) -> str:
        return obj.datum.localize()


@admin.register(_models.Verlag, site=miz_site)
class VerlagAdmin(MIZModelAdmin):
    list_display = ["verlag_name", "sitz"]
    search_form_kwargs = {"fields": ["sitz", "sitz__land", "sitz__bland"], "labels": {"sitz": "Sitz"}}
    list_select_related = ["sitz"]
    ordering = ["verlag_name", "sitz"]
    resource_class = resources.VerlagResource


@admin.register(_models.Video, site=miz_site)
class VideoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Video.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Video.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Video.person.through
        verbose_model = _models.Person

    class MusikerInLine(BaseStackedInline):
        model = _models.Video.musiker.through
        extra = 0
        filter_horizontal = ["instrument"]
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {"fields": ["musiker"]}),
            ("Instrumente", {"fields": ["instrument"], "classes": ["collapse", "collapsed"]}),
        ]
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Video.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Video.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Video.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Video.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    class AusgabeInLine(BaseAusgabeInline):
        model = _models.Ausgabe.video.through
        # Note that the tabular autocomplete widget for 'ausgabe' is created
        # by the AusgabeMagazinFieldForm of this inline class.

    class DateiInLine(BaseTabularInline):
        model = _m2m.m2m_datei_quelle
        fields = ["datei"]
        verbose_model = _models.Datei

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    form = _forms.VideoForm
    index_category = "Archivgut"
    collapse_all = True
    save_on_top = True
    list_display = ["titel", "medium", "kuenstler_list"]
    ordering = ["titel"]
    list_select_related = ["medium"]

    inlines = [
        MusikerInLine,
        BandInLine,
        SchlagwortInLine,
        GenreInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
        AusgabeInLine,
        DateiInLine,
        BestandInLine,
    ]
    # fmt: off
    fieldsets = [
        (None, {
            "fields": [
                "titel", "laufzeit", "jahr", "original", "quelle", ("medium", "medium_qty"),
                "beschreibung", "bemerkungen"
            ]
        }),
        ("Discogs", {
            "fields": ["release_id", "discogs_url"],
            "classes": ["collapse", "collapsed"]
        }),
    ]
    # fmt: on
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

    @display(description="Künstler")
    def kuenstler_list(self, obj: _models.Video) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.kuenstler_list or self.get_empty_value_display()


@admin.register(_models.Bundesland, site=miz_site)
class BlandAdmin(MIZModelAdmin):
    list_display = ["bland_name", "code", "land"]
    search_form_kwargs = {
        "fields": ["land"],
    }
    ordering = ["land", "bland_name"]


@admin.register(_models.Land, site=miz_site)
class LandAdmin(MIZModelAdmin):
    ordering = ["land_name"]


@admin.register(_models.Ort, site=miz_site)
class OrtAdmin(MIZModelAdmin):
    fields = ["stadt", "land", "bland"]  # put land before bland
    index_category = "Stammdaten"
    list_display = ["stadt", "bland", "land"]
    list_display_links = list_display
    search_form_kwargs = {"fields": ["land", "bland"], "forward": {"bland": "land"}}
    ordering = ["land", "bland", "stadt"]
    list_select_related = ["land", "bland"]
    require_confirmation = True
    resource_class = resources.OrtResource

    def formfield_for_foreignkey(self, db_field: ModelField, request: HttpRequest, **kwargs: Any) -> ChoiceField:
        if db_field == self.opts.get_field("bland"):
            # Limit the choices to the Land instance selected in 'land':
            kwargs["widget"] = make_widget(model=db_field.related_model, forward=["land"])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(_models.Bestand, site=miz_site)
class BestandAdmin(MIZModelAdmin):
    readonly_fields = [
        "audio",
        "ausgabe",
        "brochure",
        "buch",
        "dokument",
        "foto",
        "memorabilien",
        "plakat",
        "technik",
        "video",
    ]
    list_display = ["signatur", "bestand_class", "bestand_link", "lagerort", "provenienz"]
    list_select_related = ["lagerort", "provenienz__geber"]
    search_form_kwargs = {"fields": ["lagerort", "provenienz", "signatur"]}
    superuser_only = True
    require_confirmation = True
    resource_class = resources.BestandResource

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> Type[BestandChangeList]:
        return BestandChangeList

    def cache_bestand_data(self, request: HttpRequest, result_list: QuerySet, bestand_fields: list) -> None:
        """
        Use the changelist's result_list queryset to cache the data needed for
        the list display items 'bestand_class' and 'bestand_link'.

        Args:
            request (HttpRequest): the request for the changelist page
            result_list (QuerySet): result_list queryset for the results page
            bestand_fields (list): list of the ForeignKey fields of the Bestand
              model that reference models of archive objects (i.e. Ausgabe,
              Audio, etc.)
        """
        field_names = [f.name for f in bestand_fields]

        # noinspection PyAttributeOutsideInit
        self._cache = {}
        for obj in result_list.select_related(*field_names):
            relation_field = None
            for field in bestand_fields:
                if getattr(obj, field.name) is not None:
                    relation_field = field
                    break
            if not relation_field:
                continue
            self._cache[obj.pk] = {
                "bestand_class": relation_field.related_model._meta.verbose_name,
                "bestand_link": get_obj_link(request, getattr(obj, relation_field.name), namespace="admin", blank=True),
            }

    @display(description="Art")
    def bestand_class(self, obj: _models.Bestand) -> str:
        try:
            return self._cache[obj.pk]["bestand_class"]
        except KeyError:
            return ""

    @display(description="Links")
    def bestand_link(self, obj: _models.Bestand) -> Union[SafeText, str]:
        try:
            return self._cache[obj.pk]["bestand_link"]
        except KeyError:
            return ""

    def _check_search_form_fields(self, **kwargs: Any) -> list:
        # Ignore the search form fields check for BestandAdmin.
        # The check warns when a relation is missing from the search form, but
        # BestandAdmin deliberately excludes most of the relations from the
        # search form.
        return []


@admin.register(_models.Datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Datei.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Datei.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Datei.person.through
        verbose_model = _models.Person

    class MusikerInLine(BaseStackedInline):
        model = _models.Datei.musiker.through
        extra = 0
        filter_horizontal = ["instrument"]
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {"fields": ["musiker"]}),
            ("Instrumente", {"fields": ["instrument"], "classes": ["collapse", "collapsed"]}),
        ]
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Datei.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Datei.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Datei.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Datei.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    class QuelleInLine(BaseStackedInline):
        model = _m2m.m2m_datei_quelle
        extra = 0
        description = "Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei."

    actions = [_actions.merge_records, _actions.summarize]
    collapse_all = True
    index_category = "Archivgut"
    save_on_top = True
    superuser_only = True
    ordering = ["titel"]

    inlines = [
        QuelleInLine,
        GenreInLine,
        SchlagwortInLine,
        MusikerInLine,
        BandInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
    ]
    fieldsets = [
        (None, {"fields": ["titel", "media_typ", "datei_pfad", "provenienz"]}),
        ("Allgemeine Beschreibung", {"fields": ["beschreibung", "bemerkungen"]}),
    ]


@admin.register(_models.Instrument, site=miz_site)
class InstrumentAdmin(MIZModelAdmin):
    list_display = ["instrument", "kuerzel"]
    ordering = ["instrument"]
    require_confirmation = True
    resource_class = resources.InstrumentResource


@admin.register(_models.Herausgeber, site=miz_site)
class HerausgeberAdmin(MIZModelAdmin):
    ordering = ["herausgeber"]
    require_confirmation = True
    resource_class = resources.HerausgeberResource


class BaseBrochureAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through

    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear

    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    actions = [_actions.merge_records, _actions.change_bestand]
    form = _forms.BrochureForm
    index_category = "Archivgut"
    inlines = [URLInLine, JahrInLine, GenreInLine, BestandInLine]
    list_display = ["titel", "zusammenfassung", "jahr_list"]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "jahre__jahr__range"],
        "forwards": {"ausgabe": "ausgabe__magazin"},
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
    }
    # fmt: off
    fieldsets = [
        (None, {"fields": ["titel", "zusammenfassung", "beschreibung", "bemerkungen"]}),
        ("Beilage von Ausgabe", {
            "fields": [("ausgabe__magazin", "ausgabe")],
            "description": "Geben Sie die Ausgabe an, der dieses Objekt beilag.",
        }),
    ]
    # fmt: on

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        # Add the annotation necessary for the proper ordering:
        return (
            super()
            .get_queryset(request)
            .annotate(jahr_min=Min("jahre__jahr"))
            .order_by("titel", "jahr_min", "zusammenfassung")
        )

    @display(description="Jahre", ordering="jahr_min")
    def jahr_list(self, obj: _models.BaseBrochure) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.jahr_list


@admin.register(_models.Brochure, site=miz_site)
class BrochureAdmin(BaseBrochureAdmin):
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear

    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Brochure.schlagwort.through

    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    inlines = [URLInLine, JahrInLine, GenreInLine, SchlagwortInLine, BestandInLine]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "schlagwort", "jahre__jahr__range"],
        "forwards": {"ausgabe": "ausgabe__magazin"},
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe"],
    }
    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    resource_class = resources.BrochureResource


@admin.register(_models.Katalog, site=miz_site)
class KatalogAdmin(BaseBrochureAdmin):
    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    list_display = ["titel", "zusammenfassung", "art", "jahr_list"]
    resource_class = resources.KatalogResource
    # fmt: off
    fieldsets = [
        (None, {"fields": ["titel", "art", "zusammenfassung", "beschreibung", "bemerkungen"]}),
        ("Beilage von Ausgabe", {
            "fields": [("ausgabe__magazin", "ausgabe")],
            "description": "Geben Sie die Ausgabe an, der dieses Objekt beilag.",
        }),
    ]
    # fmt: on


@admin.register(_models.Kalender, site=miz_site)
class KalenderAdmin(BaseBrochureAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through

    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear

    class SpielortInLine(BaseTabularInline):
        model = _models.Kalender.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["spielort"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Kalender.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    inlines = [URLInLine, JahrInLine, GenreInLine, SpielortInLine, VeranstaltungInLine, BestandInLine]
    search_form_kwargs = {
        "fields": ["ausgabe__magazin", "ausgabe", "genre", "spielort", "veranstaltung", "jahre__jahr__range"],
        "forwards": {"ausgabe": "ausgabe__magazin"},
        "labels": {"jahre__jahr__range": "Jahr"},
        "tabular": ["ausgabe", "spielort", "veranstaltung"],
    }
    resource_class = resources.KalenderResource


@admin.register(_models.Foto, site=miz_site)
class FotoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Foto.genre.through

    class SchlagwortInLine(BaseSchlagwortInline):
        model = _models.Foto.schlagwort.through

    class PersonInLine(BaseTabularInline):
        model = _models.Foto.person.through
        verbose_model = _models.Person

    class MusikerInLine(BaseTabularInline):
        model = _models.Foto.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ["musiker"]

    class BandInLine(BaseTabularInline):
        model = _models.Foto.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ["band"]

    class OrtInLine(BaseTabularInline):
        model = _models.Foto.ort.through
        verbose_model = _models.Ort

    class SpielortInLine(BaseTabularInline):
        model = _models.Foto.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ["veranstaltung"]

    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Foto.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ["veranstaltung"]

    actions = [_actions.merge_records, _actions.change_bestand, _actions.summarize]
    collapse_all = True
    form = _forms.FotoForm
    index_category = "Archivgut"
    list_display = ["titel", "foto_id", "size", "typ", "datum_localized", "schlagwort_list"]
    readonly_fields = ["foto_id"]
    save_on_top = True
    ordering = ["titel", "datum"]

    fields = ["titel", "foto_id", "size", "typ", "farbe", "datum", "reihe", "owner", "beschreibung", "bemerkungen"]
    inlines = [
        SchlagwortInLine,
        GenreInLine,
        MusikerInLine,
        BandInLine,
        OrtInLine,
        SpielortInLine,
        VeranstaltungInLine,
        PersonInLine,
        BestandInLine,
    ]
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

    @display(description="Foto ID", ordering="id")
    def foto_id(self, obj: _models.Foto) -> str:
        """Return the id of the object, padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return str(obj.pk).zfill(6)

    @display(description="Datum", ordering="datum")
    def datum_localized(self, obj: _models.Foto) -> str:
        return obj.datum.localize()

    @display(description="Schlagwörter", ordering="schlagwort_list")
    def schlagwort_list(self, obj: _models.Foto) -> str:
        # noinspection PyUnresolvedReferences
        # (added by annotations)
        return obj.schlagwort_list or self.get_empty_value_display()


@admin.register(_models.Plattenfirma, site=miz_site)
class PlattenfirmaAdmin(MIZModelAdmin):
    search_fields = ["__ANY__"]
    require_confirmation = True
    resource_class = resources.PlattenfirmaResource


@admin.register(
    _models.Monat,
    _models.Lagerort,
    _models.Geber,
    _models.Provenienz,
    _models.Schriftenreihe,
    _models.Bildreihe,
    _models.Veranstaltungsreihe,
    _models.VideoMedium,
    _models.AudioMedium,
    site=miz_site,
)
class HiddenFromIndex(MIZModelAdmin):
    search_fields = ["__ANY__"]
    superuser_only = True
    require_confirmation = True


class AuthAdminMixin(object):
    """
    Add a model's class name to the human-readable name part of the 'permission'
    formfield choices to make the permissions more distinguishable from each
    other.

    By default, the choice's names contain the verbose_name of a model, which
    may not be unique enough to be able to differentiate between different
    permissions.
    """

    def formfield_for_manytomany(
        self, db_field: ManyToManyField, request: Optional[HttpRequest] = None, **kwargs: Any
    ) -> ChoiceField:
        """
        Get a form field for a ManyToManyField. If it is the formfield for
        Permissions, adjust the choices to include the models' class names.
        """
        formfield = super().formfield_for_manytomany(  # type: ignore[misc]
            db_field, request=request, **kwargs
        )
        if formfield.queryset.model == Permission:
            choices = []
            for perm in formfield.queryset:
                object_name = str(perm.content_type)
                # Check that the model_class that this content_type is
                # referencing exists.
                if perm.content_type.model_class():
                    object_name += " (%s)" % perm.content_type.model_class().__name__
                choices.append((perm.pk, f"{perm.content_type.app_label} | {object_name} | {perm.name}"))
            formfield.choices = choices
        return formfield


@admin.register(Group, site=miz_site)
class MIZGroupAdmin(AuthAdminMixin, GroupAdmin):
    pass


@admin.register(User, site=miz_site)
class MIZUserAdmin(AuthAdminMixin, UserAdmin):
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "activity")

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        queryset = super().get_queryset(request)
        # Note that the order_by and values calls are required:
        # see django docs expressions/#using-aggregates-within-a-subquery-expression
        recent_logs = (
            LogEntry.objects.filter(user_id=OuterRef("id"), action_time__date__gt=datetime.now() - timedelta(days=32))
            .order_by()
            .values("user_id")
        )
        subquery = Subquery(recent_logs.annotate(c=Count("*")).values("c"), output_field=IntegerField())
        return queryset.annotate(activity=Coalesce(subquery, Value(0)))

    @display(description="Aktivität letzte 30 Tage", ordering="activity")
    def activity(self, user: User) -> int:
        """Return the total amount of the recent changes made by this user."""
        # noinspection PyUnresolvedReferences
        return user.activity or 0


@admin.register(LogEntry, site=miz_site)
class MIZLogEntryAdmin(MIZAdminSearchFormMixin, LogEntryAdmin):
    fields = (
        "action_time",
        "user",
        "content_type",
        "object",
        "object_id",
        "action_flag",
        "change_message_verbose",
        "change_message_raw",
    )
    readonly_fields = ("object", "change_message_verbose", "change_message_raw")

    list_display = (
        "action_time",
        "user",
        "action_message",
        "content_type",
        "object_link",
    )
    list_filter = ()
    search_form_kwargs = {
        "fields": ("user", "content_type", "action_flag"),
        "widgets": {
            "user": autocomplete.ModelSelect2(url="autocomplete_user"),
            "content_type": autocomplete.ModelSelect2(url="autocomplete_ct"),
        },
    }

    def object(self, obj: LogEntry) -> str:
        """Return the admin link to the log entry object."""
        return self.object_link(obj)

    @display(description="Änderungsmeldung")
    def change_message_verbose(self, obj: LogEntry) -> str:
        return obj.get_change_message()

    @display(description="Datenbank-Darstellung")
    def change_message_raw(self, obj: LogEntry) -> str:
        return obj.change_message


@admin.register(Watchlist, site=miz_site)
class WatchlistAdmin(WatchlistAdmin, MIZModelAdmin):
    superuser_only = True
