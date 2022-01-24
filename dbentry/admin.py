from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type, Union

# noinspection PyPackageRequirements
from dal import autocomplete
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, Permission, User
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import (
    CharField, Count, Exists, Field as ModelField, Func, IntegerField, ManyToManyField, Min,
    OuterRef,
    QuerySet, Subquery,
    Value
)
from django.db.models.functions import Coalesce
from django.forms import BaseInlineFormSet, Field as FormField, ModelForm
from django.http import HttpRequest
from django.utils.safestring import SafeText
from django_admin_logs.admin import LogEntryAdmin

import dbentry.actions.actions as _actions
import dbentry.forms as _forms
import dbentry.m2m as _m2m
import dbentry.models as _models
from dbentry.ac.widgets import make_widget
from dbentry.base.admin import (
    BaseAliasInline, BaseAusgabeInline, BaseGenreInline, BaseOrtInLine, BaseSchlagwortInline,
    BaseStackedInline, BaseTabularInline, MIZModelAdmin
)
from dbentry.changelist import AusgabeChangeList
from dbentry.search.admin import MIZAdminSearchFormMixin
from dbentry.sites import miz_site
from dbentry.utils import concat_limit, copy_related_set
from dbentry.utils.admin import get_obj_link, log_change


# TODO: add admindocs
# (https://docs.djangoproject.com/en/2.2/ref/contrib/admin/admindocs/)


# noinspection PyProtectedMember,PyUnresolvedReferences
class BestandInLine(BaseTabularInline):
    model = _models.Bestand
    form = _forms.BestandInlineForm
    # This allows inlines.js to copy the last selected bestand to a new row.
    classes = ['copylast']
    fields = ['signatur', 'lagerort', 'provenienz', 'anmerkungen']
    readonly_fields = ['signatur']
    verbose_name = _models.Bestand._meta.verbose_name
    verbose_name_plural = _models.Bestand._meta.verbose_name_plural
    # TODO: enable tabular autocomplete for 'lagerort'
    #  (see ac.views.ACLagerort and ac.urls for details)
    # tabular_autocomplete = ['lagerort']


@admin.register(_models.Audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Audio.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Audio.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Audio.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):  # noqa
        model = _models.Audio.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Audio.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Audio.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Audio.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Audio.ort.through
        verbose_model = _models.Ort
    class PlattenInLine(BaseTabularInline):  # noqa
        model = _models.Audio.plattenfirma.through
        verbose_model = _models.Plattenfirma
    class AusgabeInLine(BaseAusgabeInline):  # noqa
        model = _models.Ausgabe.audio.through
        # Note that the tabular autocomplete widget for 'ausgabe' is created
        # by the AusgabeMagazinFieldForm of this inline class.
    class DateiInLine(BaseTabularInline):  # noqa
        model = _m2m.m2m_datei_quelle
        fields = ['datei']
        verbose_model = _models.Datei

    collapse_all = True
    form = _forms.AudioForm
    index_category = 'Archivgut'
    save_on_top = True
    list_display = ['titel', 'jahr', 'medium', 'kuenstler_string']
    list_select_related = ['medium']
    ordering = ['titel', 'jahr', 'medium']

    fieldsets = [
        (None, {
            'fields': [
                'titel', 'tracks', 'laufzeit', 'jahr', 'land_pressung', 'original', 'quelle',
                ('medium', 'medium_qty'), 'plattennummer', 'beschreibung', 'bemerkungen'
            ]
        }),
        ('Discogs', {
            'fields': ['release_id', 'discogs_url'],
            'classes': ['collapse', 'collapsed']
        }),
    ]
    inlines = [
        MusikerInLine, BandInLine, SchlInLine, GenreInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine,
        PlattenInLine, AusgabeInLine, DateiInLine, BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'plattenfirma', 'medium', 'release_id',
            'land_pressung'
        ],
        'tabular': ['musiker', 'band', 'spielort', 'veranstaltung']
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj: _models.Audio) -> str:
        # band_list and musiker_list added by annotations
        # noinspection PyUnresolvedReferences
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Ausgabe, site=miz_site)
class AusgabenAdmin(MIZModelAdmin):
    class NumInLine(BaseTabularInline):
        model = _models.AusgabeNum
        extra = 0
    class MonatInLine(BaseTabularInline):  # noqa
        model = _models.AusgabeMonat
        verbose_model = _models.Monat
        extra = 0
    class LNumInLine(BaseTabularInline):  # noqa
        model = _models.AusgabeLnum
        extra = 0
    class JahrInLine(BaseTabularInline):  # noqa
        model = _models.AusgabeJahr
        extra = 0
        verbose_name_plural = 'erschienen im Jahr'
    class AudioInLine(BaseTabularInline):  # noqa
        model = _models.Ausgabe.audio.through
        verbose_model = _models.Audio
    class VideoInLine(BaseTabularInline):  # noqa
        model = _models.Ausgabe.video.through
        verbose_model = _models.Video

    index_category = 'Archivgut'
    inlines = [
        NumInLine, MonatInLine, LNumInLine, JahrInLine, AudioInLine, VideoInLine, BestandInLine
    ]
    ordering = ['magazin__magazin_name', '_name']
    list_select_related = ['magazin']

    fields = [
        'magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang',
        'beschreibung', 'bemerkungen'
    ]
    list_display = (
        'ausgabe_name', 'num_string', 'lnum_string', 'monat_string', 'jahr_string',
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
        }
    }

    actions = [
        _actions.merge_records, _actions.bulk_jg, _actions.change_bestand,
        _actions.moveto_brochure, 'change_status_unbearbeitet',
        'change_status_inbearbeitung', 'change_status_abgeschlossen'
    ]

    def get_changelist(self, request: HttpRequest, **kwargs: Any) -> Type[AusgabeChangeList]:
        return AusgabeChangeList

    def ausgabe_name(self, obj: _models.Ausgabe) -> str:
        # noinspection PyProtectedMember
        return obj._name
    ausgabe_name.short_description = 'Ausgabe'  # type: ignore[attr-defined]  # noqa
    ausgabe_name.admin_order_field = '_name'  # type: ignore[attr-defined]  # noqa

    def magazin_name(self, obj: _models.Ausgabe) -> str:
        return obj.magazin.magazin_name
    magazin_name.short_description = 'Magazin'  # type: ignore[attr-defined]  # noqa
    magazin_name.admin_order_field = 'magazin__magazin_name'  # type: ignore[attr-defined]  # noqa

    def get_result_list_annotations(self) -> dict:
        # Can't use ArrayAgg directly to get a list of distinct monat__abk
        # values as we are ordering by monat__ordinal: using distinct AND
        # ordering requires that the ordering expressions are present in the
        # argument list to ArrayAgg.
        # Use a subquery instead:
        subquery = (
            self.model.objects.order_by().filter(id=OuterRef('id'))
            .annotate(
                x=Func(
                    ArrayAgg('ausgabemonat__monat__abk', ordering='ausgabemonat__monat__ordinal'),
                    Value(', '), Value(self.get_empty_value_display()), function='array_to_string',
                    output_field=CharField()
                )
            )
            .values('x')
        )
        return {
            'jahr_string': Func(
                ArrayAgg('ausgabejahr__jahr', distinct=True, ordering='ausgabejahr__jahr'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string',
                output_field=CharField()
            ),
            'num_string': Func(
                ArrayAgg('ausgabenum__num', distinct=True, ordering='ausgabenum__num'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string',
                output_field=CharField()
            ),
            'lnum_string': Func(
                ArrayAgg('ausgabelnum__lnum', distinct=True, ordering='ausgabelnum__lnum'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string',
                output_field=CharField()
            ),
            'monat_string': Subquery(subquery),
            'anz_artikel': Count('artikel', distinct=True)
        }

    def anz_artikel(self, obj: _models.Ausgabe) -> int:
        return obj.anz_artikel  # added by annotations  # noqa
    anz_artikel.short_description = 'Anz. Artikel'  # type: ignore[attr-defined]  # noqa
    anz_artikel.admin_order_field = 'anz_artikel'  # type: ignore[attr-defined]  # noqa

    def jahr_string(self, obj: _models.Ausgabe) -> str:
        return obj.jahr_string  # added by annotations  # noqa
    jahr_string.short_description = 'Jahre'  # type: ignore[attr-defined]  # noqa
    jahr_string.admin_order_field = 'jahr_string'  # type: ignore[attr-defined]  # noqa

    def num_string(self, obj: _models.Ausgabe) -> str:
        return obj.num_string  # added by annotations  # noqa
    num_string.short_description = 'Nummer'  # type: ignore[attr-defined]  # noqa
    num_string.admin_order_field = 'num_string'  # type: ignore[attr-defined]  # noqa

    def lnum_string(self, obj: _models.Ausgabe) -> str:
        return obj.lnum_string  # added by annotations  # noqa
    lnum_string.short_description = 'lfd. Nummer'  # type: ignore[attr-defined]  # noqa
    lnum_string.admin_order_field = 'lnum_string'  # type: ignore[attr-defined]  # noqa

    def monat_string(self, obj: _models.Ausgabe) -> str:
        return obj.monat_string  # added by annotations  # noqa
    monat_string.short_description = 'Monate'  # type: ignore[attr-defined]  # noqa
    monat_string.admin_order_field = 'monat_string'  # type: ignore[attr-defined]  # noqa

    def _change_status(self, request: HttpRequest, queryset: QuerySet, status: str) -> None:
        """Update the ``status`` of the Ausgabe instances in ``queryset``."""
        with transaction.atomic():
            queryset.update(status=status, _changed_flag=False)
        try:
            with transaction.atomic():
                for obj in queryset:
                    # noinspection PyUnresolvedReferences
                    log_change(request.user.pk, obj, fields=['status'])
        except Exception as e:
            message_text = (
                "Fehler beim Erstellen der LogEntry Objekte: \n"
                "%(error_class)s: %(error_txt)s" % {
                    'error_class': e.__class__.__name__, 'error_txt': e.args[0]}
            )
            self.message_user(request, message_text, 'ERROR')

    def change_status_unbearbeitet(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        UNBEARBEITET.
        """
        self._change_status(request, queryset, _models.Ausgabe.UNBEARBEITET)
    change_status_unbearbeitet.allowed_permissions = ['change']  # type: ignore[attr-defined]  # noqa
    change_status_unbearbeitet.short_description = 'Status ändern: unbearbeitet'  # type: ignore[attr-defined]  # noqa

    def change_status_inbearbeitung(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        INBEARBEITUNG.
        """
        self._change_status(request, queryset, _models.Ausgabe.INBEARBEITUNG)
    change_status_inbearbeitung.allowed_permissions = ['change']  # type: ignore[attr-defined]  # noqa
    change_status_inbearbeitung.short_description = 'Status ändern: in Bearbeitung'  # type: ignore[attr-defined]  # noqa

    def change_status_abgeschlossen(self, request: HttpRequest, queryset: QuerySet) -> None:
        """
        Set the ``status`` of the Ausgabe instances in ``queryset`` to
        ABGESCHLOSSEN.
        """
        self._change_status(request, queryset, _models.Ausgabe.ABGESCHLOSSEN)
    change_status_abgeschlossen.allowed_permissions = ['change']  # type: ignore[attr-defined]  # noqa
    change_status_abgeschlossen.short_description = 'Status ändern: abgeschlossen'  # type: ignore[attr-defined]  # noqa

    @staticmethod
    def has_moveto_brochure_permission(request: HttpRequest) -> bool:
        """
        Check that the request's user has permission to add Brochure objects
        and permission to delete Ausgabe objects.
        """
        from django.contrib.auth import get_permission_codename
        perms = []
        # noinspection PyUnresolvedReferences,PyProtectedMember
        for name, opts in [('delete', _models.Ausgabe._meta), ('add', _models.BaseBrochure._meta)]:
            perms.append("%s.%s" % (opts.app_label, get_permission_codename(name, opts)))
        # noinspection PyUnresolvedReferences
        return request.user.has_perms(perms)

    def _get_crosslink_relations(self):
        return [
            (_models.Artikel, 'ausgabe', 'Artikel'),
            (_models.Brochure, 'ausgabe', 'Broschüren'),
            (_models.Kalender, 'ausgabe', 'Programmhefte'),
            (_models.Katalog, 'ausgabe', 'Warenkataloge'),
        ]


@admin.register(_models.Autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = _models.Autor.magazin.through
        verbose_model = _models.Magazin
        extra = 1
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.AutorURL

    form = _forms.AutorForm
    index_category = 'Stammdaten'
    inlines = [URLInLine, MagazinInLine]
    list_display = ['autor_name', 'person', 'kuerzel', 'magazin_string']
    list_select_related = ['person']
    search_form_kwargs = {'fields': ['magazin', 'person']}
    ordering = ['_name']

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'magazin_list': ArrayAgg(
                'magazin__magazin_name', distinct=True, ordering='magazin__magazin_name'),
        }

    def autor_name(self, obj: _models.Autor) -> str:
        # noinspection PyProtectedMember
        return obj._name
    autor_name.short_description = 'Autor'  # type: ignore[attr-defined]  # noqa
    autor_name.admin_order_field = '_name'  # type: ignore[attr-defined]  # noqa

    def magazin_string(self, obj: _models.Autor) -> str:
        return concat_limit(obj.magazin_list) or self.get_empty_value_display() # added by annotations  # noqa
    magazin_string.short_description = 'Magazin(e)'  # type: ignore[attr-defined]  # noqa
    magazin_string.admin_order_field = 'magazin_list'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Artikel, site=miz_site)
class ArtikelAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Artikel.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Artikel.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.person.through
        verbose_model = _models.Person
    class AutorInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.autor.through
        verbose_model = _models.Autor
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['spielort']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Artikel.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']

    form = _forms.ArtikelForm
    index_category = 'Archivgut'
    save_on_top = True
    list_select_related = ['ausgabe', 'ausgabe__magazin']
    ordering = [
        'ausgabe__magazin__magazin_name', 'ausgabe___name', 'seite', 'schlagzeile']

    fields = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'),
        'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]
    inlines = [
        AutorInLine, MusikerInLine, BandInLine, SchlInLine, GenreInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine
    ]
    list_display = [
        'schlagzeile', 'zusammenfassung_string', 'seite', 'schlagwort_string',
        'ausgabe_name', 'artikel_magazin', 'kuenstler_string'
    ]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'autor', 'musiker', 'band',
            'schlagwort', 'genre', 'ort', 'spielort', 'veranstaltung', 'person',
            'seite__range'
        ],
        'forwards': {'ausgabe': 'ausgabe__magazin'},
        'tabular': ['ausgabe', 'musiker', 'band', 'spielort', 'veranstaltung']
    }

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'schlagwort_list': ArrayAgg(
                'schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort'),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def ausgabe_name(self, obj: _models.Artikel) -> str:
        # noinspection PyProtectedMember
        return obj.ausgabe._name
    ausgabe_name.short_description = 'Ausgabe'  # type: ignore[attr-defined]  # noqa
    ausgabe_name.admin_order_field = 'ausgabe___name'  # type: ignore[attr-defined]  # noqa

    def zusammenfassung_string(self, obj: _models.Artikel) -> str:
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)
    zusammenfassung_string.short_description = 'Zusammenfassung'  # type: ignore[attr-defined]  # noqa
    zusammenfassung_string.admin_order_field = 'zusammenfassung'  # type: ignore[attr-defined]  # noqa

    def artikel_magazin(self, obj: _models.Artikel) -> str:
        return obj.ausgabe.magazin.magazin_name
    artikel_magazin.short_description = 'Magazin'  # type: ignore[attr-defined]  # noqa
    artikel_magazin.admin_order_field = 'ausgabe__magazin__magazin_name'  # type: ignore[attr-defined]  # noqa

    def schlagwort_string(self, obj: _models.Artikel) -> str:
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display() # added by annotations  # noqa
    schlagwort_string.short_description = 'Schlagwörter'  # type: ignore[attr-defined]  # noqa
    schlagwort_string.admin_order_field = 'schlagwort_list'  # type: ignore[attr-defined]  # noqa

    def kuenstler_string(self, obj: _models.Artikel) -> str:
        # band_list and musiker_list added by annotations
        # noinspection PyUnresolvedReferences
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Band, site=miz_site)
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Band.genre.through
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Band.musiker.through
        verbose_name = 'Band-Mitglied'
        verbose_name_plural = 'Band-Mitglieder'
        tabular_autocomplete = ['musiker']
    class AliasInLine(BaseAliasInline):  # noqa
        model = _models.BandAlias
    class OrtInLine(BaseOrtInLine):  # noqa
        model = _models.Band.orte.through
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.BandURL

    form = _forms.BandForm
    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, AliasInLine, MusikerInLine, OrtInLine]
    list_display = ['band_name', 'genre_string', 'musiker_string', 'orte_string']
    save_on_top = True
    ordering = ['band_name']

    search_form_kwargs = {
        'fields': ['musiker', 'genre', 'orte__land', 'orte'],
        'labels': {'musiker': 'Mitglied'},
        'tabular': ['musiker']
    }

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'genre_list': ArrayAgg('genre__genre', distinct=True, ordering='genre__genre'),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'alias_list': ArrayAgg(
                'bandalias__alias', distinct=True, ordering='bandalias__alias'),
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name')
        }

    def genre_string(self, obj: _models.Band) -> str:
        return concat_limit(obj.genre_list) or self.get_empty_value_display()  # added by annotations  # noqa
    genre_string.short_description = 'Genres'  # type: ignore[attr-defined]  # noqa
    genre_string.admin_order_field = 'genre_list'  # type: ignore[attr-defined]  # noqa

    def musiker_string(self, obj: _models.Band) -> str:
        return concat_limit(obj.musiker_list) or self.get_empty_value_display()  # added by annotations  # noqa
    musiker_string.short_description = 'Mitglieder'  # type: ignore[attr-defined]  # noqa
    musiker_string.admin_order_field = 'musiker_list'  # type: ignore[attr-defined]  # noqa

    def alias_string(self, obj: _models.Band) -> str:
        return concat_limit(obj.alias_list) or self.get_empty_value_display()  # added by annotations  # noqa
    alias_string.short_description = 'Aliase'  # type: ignore[attr-defined]  # noqa
    alias_string.admin_order_field = 'alias_list'  # type: ignore[attr-defined]  # noqa

    def orte_string(self, obj: _models.Band) -> str:
        return concat_limit(obj.orte_list, sep="; ") or self.get_empty_value_display()  # added by annotations  # noqa
    orte_string.short_description = 'Orte'  # type: ignore[attr-defined]  # noqa
    orte_string.admin_order_field = 'orte_list'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Plakat, site=miz_site)  # noqa
class PlakatAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Plakat.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Plakat.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Plakat.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']

    collapse_all = True
    form = _forms.PlakatForm
    index_category = 'Archivgut'
    list_display = ['titel', 'plakat_id', 'size', 'datum_localized', 'veranstaltung_string']
    readonly_fields = ['plakat_id']
    save_on_top = True
    ordering = ['titel', 'datum']
    fields = [
        'titel', 'plakat_id', 'size', 'datum', 'reihe', 'copy_related',
        'beschreibung', 'bemerkungen'
    ]

    inlines = [
        SchlInLine, GenreInLine, MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'reihe', 'datum__range', 'signatur__contains'
        ],
        'labels': {'reihe': 'Bildreihe'},
        'tabular': ['musiker', 'band', 'spielort', 'veranstaltung']
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'veranstaltung_list':
                ArrayAgg('veranstaltung__name', distinct=True, ordering='veranstaltung__name')
        }

    def datum_localized(self, obj: _models.Plakat) -> str:
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'  # type: ignore[attr-defined]  # noqa
    datum_localized.admin_order_field = 'datum'  # type: ignore[attr-defined]  # noqa

    def veranstaltung_string(self, obj: _models.Plakat) -> str:
        return concat_limit(obj.veranstaltung_list) or self.get_empty_value_display()  # added by annotations  # noqa
    veranstaltung_string.short_description = 'Veranstaltungen'  # type: ignore[attr-defined]  # noqa
    veranstaltung_string.admin_order_field = 'veranstaltung_list'  # type: ignore[attr-defined]  # noqa

    def get_fields(self, request: HttpRequest, obj: _models.Plakat = None) -> List[str]:
        """
        Remove the 'copy_related' formfield if the user does not have change
        permissions on the object.
        """
        fields = super().get_fields(request, obj)
        if obj is None:
            return fields
        # Remove the 'copy_related' field from the change form if the user
        # only has view permissions and thus can't use copy_related.
        if not (obj and hasattr(request, 'user') and 'copy_related' in fields):
            # Either this is an 'add' form or 'copy_related' isn't even
            # included in the fields.
            #
            # request.user is set by AuthenticationMiddleware to either an
            # auth.User instance or an AnonymousUser instance. Only mocked
            # request objects would bypass the middleware, which could allow
            # a request object to *not* have a user attribute.
            # NOTE: Honestly, I'm not sure why I am checking for the attribute
            # here (I'm assuming it's for tests), but I'm just going to leave
            # it in.
            return fields
        has_change_perms = self.has_change_permission(request, obj)
        if not (obj.pk and has_change_perms) and 'copy_related' in fields:
            # Return a copy without 'copy_related':
            return [f for f in fields if f != 'copy_related']
        return fields

    def save_related(
            self,
            request: HttpRequest,
            form: ModelForm,
            formsets: List[BaseInlineFormSet],
            change: bool
    ) -> None:
        super().save_related(request, form, formsets, change)
        self._copy_related(request, form.instance)

    @staticmethod
    def _copy_related(request: HttpRequest, obj: _models.Plakat) -> None:
        """Copy Band and Musiker instances of Veranstaltung to this object."""
        if 'copy_related' in request.POST:
            copy_related_set(
                request, obj, 'veranstaltung__band', 'veranstaltung__musiker'
            )

    def plakat_id(self, obj: _models.Plakat) -> str:
        """ID of this instance, with a prefixed 'P' and padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return "P" + str(obj.pk).zfill(6)
    plakat_id.short_description = 'Plakat ID'  # type: ignore[attr-defined]  # noqa
    plakat_id.admin_order_field = 'id'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Buch.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Buch.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Buch.person.through
        verbose_model = _models.Person
    class AutorInLine(BaseTabularInline):  # noqa
        model = _models.Buch.autor.through
        verbose_model = _models.Autor
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Buch.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Buch.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Buch.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Buch.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Buch.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']
    class HerausgeberInLine(BaseTabularInline):  # noqa
        model = _models.Buch.herausgeber.through
        verbose_model = _models.Herausgeber
    class VerlagInLine(BaseTabularInline):  # noqa
        model = _models.Buch.verlag.through
        verbose_model = _models.Verlag

    collapse_all = True
    # TODO: Semantik: Einzelbänder/Aufsätze: Teile eines Buchbandes
    crosslink_labels = {'buch': 'Aufsätze'}
    form = _forms.BuchForm
    index_category = 'Archivgut'
    save_on_top = True
    ordering = ['titel']

    fieldsets = [
        (None, {
            'fields': [
                'titel', 'seitenumfang', 'jahr', 'auflage', 'schriftenreihe',
                ('buchband', 'is_buchband'), 'ISBN', 'EAN', 'sprache',
                'beschreibung', 'bemerkungen'
            ]
        }),
        ('Original Angaben (bei Übersetzung)', {
            'fields': ['titel_orig', 'jahr_orig'],
            'description': "Angaben zum Original eines übersetzten Buches.",
            'classes': ['collapse', 'collapsed'],
        }),
    ]
    inlines = [
        AutorInLine, MusikerInLine, BandInLine, SchlInLine, GenreInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, HerausgeberInLine, VerlagInLine, BestandInLine
    ]
    list_display = [
        'titel', 'seitenumfang', 'autoren_string', 'kuenstler_string',
        'schlagwort_string', 'genre_string'
    ]
    search_form_kwargs = {
        'fields': [
            'autor', 'musiker', 'band', 'schlagwort', 'genre', 'ort',
            'spielort', 'veranstaltung', 'person', 'herausgeber', 'verlag',
            'schriftenreihe', 'buchband', 'jahr', 'ISBN', 'EAN'
        ],
        'tabular': ['musiker', 'band', 'spielort', 'veranstaltung'],
        # 'autor' help_text refers to quick item creation which is not allowed
        # in search forms - disable the help_text.
        'help_texts': {'autor': None}
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'autor_list': ArrayAgg('autor___name', distinct=True, ordering='autor___name'),
            'schlagwort_list': ArrayAgg(
                'schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort'),
            'genre_list': ArrayAgg('genre__genre', distinct=True, ordering='genre__genre'),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def autoren_string(self, obj: _models.Buch) -> str:
        return concat_limit(obj.autor_list) or self.get_empty_value_display() # added by annotations  # noqa
    autoren_string.short_description = 'Autoren'  # type: ignore[attr-defined]  # noqa
    autoren_string.admin_order_field = 'autor_list'  # type: ignore[attr-defined]  # noqa

    def schlagwort_string(self, obj: _models.Buch) -> str:
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display() # added by annotations  # noqa
    schlagwort_string.short_description = 'Schlagwörter'  # type: ignore[attr-defined]  # noqa
    schlagwort_string.admin_order_field = 'schlagwort_list'  # type: ignore[attr-defined]  # noqa

    def genre_string(self, obj: _models.Buch) -> str:
        return concat_limit(obj.genre_list) or self.get_empty_value_display() # added by annotations  # noqa
    genre_string.short_description = 'Genres'  # type: ignore[attr-defined]  # noqa
    genre_string.admin_order_field = 'genre_list'  # type: ignore[attr-defined]  # noqa

    def kuenstler_string(self, obj: _models.Buch) -> str:
        #  band_list and musiker_list added by annotations
        # noinspection PyUnresolvedReferences
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Dokument, site=miz_site)
class DokumentAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ['titel']
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Genre, site=miz_site)
class GenreAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.GenreAlias

    index_category = 'Stammdaten'
    inlines = [AliasInLine]
    list_display = ['genre', 'alias_string']
    ordering = ['genre']

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'alias_list': ArrayAgg('genrealias__alias', ordering='genrealias__alias')
        }

    def alias_string(self, obj: _models.Genre) -> str:
        return concat_limit(obj.alias_list) or self.get_empty_value_display() # added by annotations  # noqa
    alias_string.short_description = 'Aliase'  # type: ignore[attr-defined]  # noqa

    def _get_crosslink_relations(self):
        return [
            (_models.Musiker, 'genre', None), (_models.Band, 'genre', None),
            (_models.Magazin, 'genre', None), (_models.Artikel, 'genre', None),
            (_models.Buch, 'genre', None), (_models.Audio, 'genre', None),
            (_models.Plakat, 'genre', None), (_models.Dokument, 'genre', None),
            (_models.Memorabilien, 'genre', None), (_models.Technik, 'genre', None),
            (_models.Veranstaltung, 'genre', None), (_models.Video, 'genre', None),
            (_models.Datei, 'genre', None), (_models.Brochure, 'genre', None),
            (_models.Kalender, 'genre', None), (_models.Katalog, 'genre', None),
            (_models.Foto, 'genre', None)
        ]


@admin.register(_models.Magazin, site=miz_site)
class MagazinAdmin(MIZModelAdmin):
    class URLInLine(BaseTabularInline):
        model = _models.MagazinURL
    class VerlagInLine(BaseTabularInline):  # noqa
        model = _models.Magazin.verlag.through
        verbose_model = _models.Verlag
    class HerausgeberInLine(BaseTabularInline):  # noqa
        model = _models.Magazin.herausgeber.through
        verbose_model = _models.Herausgeber
    class GenreInLine(BaseGenreInline):  # noqa
        model = _models.Magazin.genre.through
    class OrtInLine(BaseOrtInLine):  # noqa
        model = _models.Magazin.orte.through

    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, VerlagInLine, HerausgeberInLine, OrtInLine]
    list_display = ['magazin_name', 'short_beschreibung', 'orte_string', 'anz_ausgaben']
    ordering = ['magazin_name']

    search_form_kwargs = {
        'fields': ['verlag', 'herausgeber', 'orte', 'genre', 'issn', 'fanzine'],
    }

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name'),
            'anz_ausgaben': Count('ausgabe', distinct=True)
        }

    def anz_ausgaben(self, obj: _models.Magazin) -> int:
        return obj.anz_ausgaben # added by annotations  # noqa
    anz_ausgaben.short_description = 'Anz. Ausgaben'  # type: ignore[attr-defined]  # noqa
    anz_ausgaben.admin_order_field = 'anz_ausgaben'  # type: ignore[attr-defined]  # noqa

    def orte_string(self, obj: _models.Magazin) -> str:
        return concat_limit(obj.orte_list, sep="; ") or self.get_empty_value_display() # added by annotations  # noqa
    orte_string.short_description = 'Orte'  # type: ignore[attr-defined]  # noqa
    orte_string.admin_order_field = 'orte_list'  # type: ignore[attr-defined]  # noqa

    def short_beschreibung(self, obj: _models.Magazin) -> str:
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")
    short_beschreibung.short_description = 'Beschreibung'  # type: ignore[attr-defined]  # noqa
    short_beschreibung.admin_order_field = 'beschreibung'  # type: ignore[attr-defined]  # noqa

    def get_exclude(self, request: HttpRequest, obj: Optional[_models.Magazin] = None) -> List[str]:
        """
        Exclude 'ausgaben_merkmal' from the add/change page if the current
        user is not a superuser.
        """
        exclude = super().get_exclude(request, obj) or []
        # noinspection PyUnresolvedReferences
        if not request.user.is_superuser:
            exclude = list(exclude)  # Copy the iterable.
            exclude.append('ausgaben_merkmal')
        return exclude


@admin.register(_models.Memorabilien, site=miz_site)
class MemoAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ['titel']
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Musiker, site=miz_site)
class MusikerAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Musiker.genre.through
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
        tabular_autocomplete = ['band']
    class AliasInLine(BaseAliasInline):  # noqa
        model = _models.MusikerAlias
    class InstrInLine(BaseTabularInline):  # noqa
        model = _models.Musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    class OrtInLine(BaseOrtInLine):  # noqa
        model = _models.Musiker.orte.through
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.MusikerURL

    form = _forms.MusikerForm
    fields = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, AliasInLine, BandInLine, OrtInLine, InstrInLine]
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'orte_string']
    save_on_top = True
    search_form_kwargs = {'fields': ['person', 'genre', 'instrument', 'orte__land', 'orte']}
    ordering = ['kuenstler_name']

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'band_list': ArrayAgg('band__band_name', distinct=True, ordering='band__band_name'),
            'genre_list': ArrayAgg('genre__genre', distinct=True, ordering='genre__genre'),
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name')
        }

    def band_string(self, obj: _models.Musiker) -> str:
        return concat_limit(obj.band_list) or self.get_empty_value_display()  # added by annotations # noqa
    band_string.short_description = 'Bands'  # type: ignore[attr-defined]  # noqa
    band_string.admin_order_field = 'band_list'  # type: ignore[attr-defined]  # noqa

    def genre_string(self, obj: _models.Musiker) -> str:
        return concat_limit(obj.genre_list) or self.get_empty_value_display()  # added by annotations # noqa
    genre_string.short_description = 'Genres'  # type: ignore[attr-defined]  # noqa
    genre_string.admin_order_field = 'genre_list'  # type: ignore[attr-defined]  # noqa

    def orte_string(self, obj: _models.Musiker) -> str:
        return concat_limit(obj.orte_list, sep="; ") or self.get_empty_value_display()  # added by annotations # noqa
    orte_string.short_description = 'Orte'  # type: ignore[attr-defined]  # noqa
    orte_string.admin_order_field = 'orte_list'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = _models.Person.orte.through
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.PersonURL

    index_category = 'Stammdaten'
    inlines = [URLInLine, OrtInLine]
    list_display = ('vorname', 'nachname', 'orte_string', 'is_musiker', 'is_autor')
    list_display_links = ['vorname', 'nachname']
    ordering = ['nachname', 'vorname']
    form = _forms.PersonForm

    fieldsets = [
        (None, {
            'fields': ['vorname', 'nachname', 'beschreibung', 'bemerkungen'],
        }),
        ('Gemeinsame Normdatei', {
            'fields': ['gnd_id', 'gnd_name', 'dnb_url'],
            'classes': ['collapse', 'collapsed'],
        })
    ]

    search_form_kwargs = {
        'fields': ['orte', 'orte__land', 'orte__bland', 'gnd_id'],
        'forwards': {'orte__bland': 'orte__land'}
    }

    def get_result_list_annotations(self) -> dict:
        return {
            'is_musiker': Exists(
                _models.Musiker.objects.only('id').filter(person_id=OuterRef('id'))),
            'is_autor': Exists(
                _models.Autor.objects.only('id').filter(person_id=OuterRef('id'))),
            'orte_list': ArrayAgg(
                'orte___name', distinct=True, ordering='orte___name')
        }

    def is_musiker(self, obj: _models.Person) -> bool:
        return obj.is_musiker  # added by annotations # noqa
    is_musiker.short_description = 'Ist Musiker'  # type: ignore[attr-defined]  # noqa
    is_musiker.boolean = True  # type: ignore[attr-defined]  # noqa

    def is_autor(self, obj: _models.Person) -> bool:
        return obj.is_autor  # added by annotations # noqa
    is_autor.short_description = 'Ist Autor'  # type: ignore[attr-defined]  # noqa
    is_autor.boolean = True  # type: ignore[attr-defined]  # noqa

    def orte_string(self, obj: _models.Person) -> str:
        return concat_limit(obj.orte_list, sep="; ") or self.get_empty_value_display()  # added by annotations # noqa
    orte_string.short_description = 'Orte'  # type: ignore[attr-defined]  # noqa
    orte_string.admin_order_field = 'orte_list'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Schlagwort, site=miz_site)
class SchlagwortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SchlagwortAlias
        extra = 1

    index_category = 'Stammdaten'
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string']
    ordering = ['schlagwort']

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'alias_list': ArrayAgg('schlagwortalias__alias', ordering='schlagwortalias__alias')
        }

    def alias_string(self, obj: _models.Schlagwort) -> str:
        return concat_limit(obj.alias_list) or self.get_empty_value_display()  # added by annotations # noqa
    alias_string.short_description = 'Aliase'  # type: ignore[attr-defined]  # noqa
    alias_string.admin_order_field = 'alias_list'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Spielort, site=miz_site)
class SpielortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SpielortAlias
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.SpielortURL

    list_display = ['name', 'ort']
    inlines = [URLInLine, AliasInLine]
    search_form_kwargs = {'fields': ['ort', 'ort__land']}
    ordering = ['name', 'ort']
    list_select_related = ['ort']


@admin.register(_models.Technik, site=miz_site)
class TechnikAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True
    ordering = ['titel']
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Veranstaltung, site=miz_site)
class VeranstaltungAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Veranstaltung.genre.through
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Veranstaltung.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Veranstaltung.person.through
        verbose_model = _models.Person
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Veranstaltung.schlagwort.through
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Veranstaltung.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ['musiker']
    class AliasInLine(BaseAliasInline):  # noqa
        model = _models.VeranstaltungAlias
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.VeranstaltungURL

    collapse_all = True
    inlines = [
        URLInLine, AliasInLine, MusikerInLine, BandInLine, SchlInLine,
        GenreInLine, PersonInLine
    ]
    list_display = ['name', 'datum_localized', 'spielort', 'kuenstler_string']
    save_on_top = True
    ordering = ['name', 'spielort', 'datum']
    tabular_autocomplete = ['spielort']
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'person', 'spielort',
            'reihe', 'datum__range'
        ],
        'tabular': ['musiker', 'band'],
    }

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj: _models.Veranstaltung) -> str:
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()  # added by annotations # noqa
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa

    def datum_localized(self, obj: _models.Veranstaltung) -> str:
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'  # type: ignore[attr-defined]  # noqa
    datum_localized.admin_order_field = 'datum'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Verlag, site=miz_site)
class VerlagAdmin(MIZModelAdmin):
    list_display = ['verlag_name', 'sitz']
    search_form_kwargs = {
        'fields': ['sitz', 'sitz__land', 'sitz__bland'],
        'labels': {'sitz': 'Sitz'}
    }
    list_select_related = ['sitz']
    ordering = ['verlag_name', 'sitz']


@admin.register(_models.Video, site=miz_site)
class VideoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Video.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Video.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Video.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):  # noqa
        model = _models.Video.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Video.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Video.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Video.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Video.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']
    class AusgabeInLine(BaseAusgabeInline):  # noqa
        model = _models.Ausgabe.video.through
        # Note that the tabular autocomplete widget for 'ausgabe' is created
        # by the AusgabeMagazinFieldForm of this inline class.
    class DateiInLine(BaseTabularInline):  # noqa
        model = _m2m.m2m_datei_quelle
        fields = ['datei']
        verbose_model = _models.Datei

    form = _forms.VideoForm
    index_category = 'Archivgut'
    collapse_all = True
    save_on_top = True
    list_display = ['titel', 'medium', 'kuenstler_string']
    ordering = ['titel']
    list_select_related = ['medium']

    inlines = [
        MusikerInLine, BandInLine,
        SchlInLine, GenreInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, AusgabeInLine, DateiInLine, BestandInLine
    ]
    fieldsets = [
        (None, {
            'fields': [
                'titel', 'laufzeit', 'jahr', 'original', 'quelle', ('medium', 'medium_qty'),
                'beschreibung', 'bemerkungen'
            ]
        }),
        ('Discogs', {
            'fields': ['release_id', 'discogs_url'],
            'classes': ['collapse', 'collapsed']
        }),
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'medium', 'release_id'
        ],
        'tabular': ['musiker', 'band', 'spielort', 'veranstaltung'],
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj: _models.Video) -> str:
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()  # added by annotations # noqa
    kuenstler_string.short_description = 'Künstler'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Bundesland, site=miz_site)
class BlandAdmin(MIZModelAdmin):
    list_display = ['bland_name', 'code', 'land']
    search_form_kwargs = {
        'fields': ['land'],
    }
    ordering = ['land', 'bland_name']


@admin.register(_models.Land, site=miz_site)
class LandAdmin(MIZModelAdmin):
    ordering = ['land_name']


@admin.register(_models.Ort, site=miz_site)
class OrtAdmin(MIZModelAdmin):
    fields = ['stadt', 'land', 'bland']  # put land before bland
    index_category = 'Stammdaten'
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    search_form_kwargs = {'fields': ['land', 'bland']}
    ordering = ['land', 'bland', 'stadt']
    list_select_related = ['land', 'bland']

    def formfield_for_foreignkey(
            self, db_field: ModelField, request: HttpRequest, **kwargs: Any
    ) -> FormField:
        if db_field == self.opts.get_field('bland'):
            # Limit the choices to the Land instance selected in 'land':
            kwargs['widget'] = make_widget(model=db_field.related_model, forward=['land'])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(_models.Bestand, site=miz_site)
class BestandAdmin(MIZModelAdmin):
    readonly_fields = [
        'audio', 'ausgabe', 'brochure', 'buch', 'dokument', 'foto',
        'memorabilien', 'plakat', 'technik', 'video'
    ]
    list_display = ['signatur', 'bestand_class', 'bestand_link', 'lagerort', 'provenienz']
    search_form_kwargs = {'fields': ['lagerort', 'signatur']}
    superuser_only = True
    # FIXME: the search form is missing a text search element ('q')
    # FIXME: the search form is missing a 'show all'

    def get_queryset(self, request: HttpRequest, **kwargs: Any) -> QuerySet:
        # noinspection PyAttributeOutsideInit
        self.request = request  # save the request for bestand_link()
        return super().get_queryset(request)

    def bestand_class(self, obj: _models.Bestand) -> str:
        if obj.bestand_object:
            # noinspection PyProtectedMember,PyUnresolvedReferences
            return obj.bestand_object._meta.verbose_name
        return ''
    bestand_class.short_description = 'Art'  # type: ignore[attr-defined]  # noqa

    def bestand_link(self, obj: _models.Bestand) -> Union[SafeText, str]:
        if obj.bestand_object:
            # noinspection PyUnresolvedReferences
            return get_obj_link(obj.bestand_object, self.request.user, blank=True)
        return ''
    bestand_link.short_description = 'Link'  # type: ignore[attr-defined]  # noqa

    def _check_search_form_fields(self, **kwargs: Any) -> list:
        # Ignore the search form fields check for BestandAdmin.
        return []


@admin.register(_models.Datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Datei.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Datei.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Datei.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):  # noqa
        model = _models.Datei.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Datei.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Datei.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Datei.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Datei.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']
    class QuelleInLine(BaseStackedInline):  # noqa
        model = _m2m.m2m_datei_quelle
        extra = 0
        description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'

    collapse_all = True
    index_category = 'Archivgut'
    save_on_top = True
    superuser_only = True
    ordering = ['titel']

    inlines = [
        QuelleInLine, GenreInLine, SchlInLine,
        MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine,
    ]
    fieldsets = [
        (None, {'fields': ['titel', 'media_typ', 'datei_pfad', 'provenienz']}),
        ('Allgemeine Beschreibung', {'fields': ['beschreibung', 'bemerkungen']}),
    ]


@admin.register(_models.Instrument, site=miz_site)
class InstrumentAdmin(MIZModelAdmin):
    list_display = ['instrument', 'kuerzel']
    ordering = ['instrument']


@admin.register(_models.Herausgeber, site=miz_site)
class HerausgeberAdmin(MIZModelAdmin):
    ordering = ['herausgeber']


class BaseBrochureAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through
    class JahrInLine(BaseTabularInline):  # noqa
        model = _models.BrochureYear
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.BrochureURL

    form = _forms.BrochureForm
    index_category = 'Archivgut'
    inlines = [URLInLine, JahrInLine, GenreInLine, BestandInLine]
    list_display = ['titel', 'zusammenfassung', 'jahr_string']
    search_form_kwargs = {
        'fields': ['ausgabe__magazin', 'ausgabe', 'genre', 'jahre__jahr__range'],
        'forwards': {'ausgabe': 'ausgabe__magazin'},
        'labels': {'jahre__jahr__range': 'Jahr'},
        'tabular': ['ausgabe']
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_fieldsets(self, request: HttpRequest, obj: _models.BaseBrochure = None) -> list:
        """Add a fieldset for (ausgabe, ausgabe__magazin)."""
        fieldsets = super().get_fieldsets(request, obj)
        # django default implementation adds at minimum:
        # [(None, {'fields': self.get_fields()})]
        # Check the default fieldset for (ausgabe, ausgabe__magazin).
        # 'ausgabe__magazin' is returned by get_fields() due to being a base
        # field of this ModelAdmin's form class.
        default_fieldset = dict(fieldsets).get(None, None)
        if not default_fieldset:
            return fieldsets
        fields = default_fieldset['fields'].copy()
        ausgabe_fields = ('ausgabe__magazin', 'ausgabe')
        if all(f in fields for f in ausgabe_fields):
            for f in ausgabe_fields:
                fields.remove(f)
            fieldset = (
                'Beilage von Ausgabe', {
                    'fields': [ausgabe_fields],
                    'description': 'Geben Sie die Ausgabe an, der dieses Objekt beilag.'
                }
            )
            fieldsets.insert(1, fieldset)
            default_fieldset['fields'] = fields
        return fieldsets

    def get_queryset(self, request):
        # Add the annotation necessary for the proper ordering:
        return super().get_queryset(request).annotate(jahr_min=Min('jahre__jahr')).order_by(
            'titel', 'jahr_min', 'zusammenfassung'
        )

    def get_result_list_annotations(self) -> dict:
        return {
            'jahr_string': Func(
                ArrayAgg('jahre__jahr', distinct=True, ordering='jahre__jahr'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string',
                output_field=CharField()
            ),
        }

    def jahr_string(self, obj: _models.BaseBrochure) -> str:
        return obj.jahr_string  # added by annotations  # noqa
    jahr_string.short_description = 'Jahre'  # type: ignore[attr-defined]  # noqa
    jahr_string.admin_order_field = 'jahr_min'  # type: ignore[attr-defined]  # noqa


@admin.register(_models.Brochure, site=miz_site)
class BrochureAdmin(BaseBrochureAdmin):
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear
    class GenreInLine(BaseGenreInline):  # noqa
        model = _models.BaseBrochure.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Brochure.schlagwort.through
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.BrochureURL

    inlines = [URLInLine, JahrInLine, GenreInLine, SchlInLine, BestandInLine]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'genre', 'schlagwort',
            'jahre__jahr__range'
        ],
        'forwards': {'ausgabe': 'ausgabe__magazin'},
        'labels': {'jahre__jahr__range': 'Jahr'},
        'tabular': ['ausgabe']
    }
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Katalog, site=miz_site)
class KatalogAdmin(BaseBrochureAdmin):

    list_display = ['titel', 'zusammenfassung', 'art', 'jahr_string']
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_fieldsets(self, *args: Any, **kwargs: Any) -> list:
        """
        Swap fieldset fields 'art' and 'zusammenfassung' without having to
        redeclare the entire fieldsets attribute.
        """
        fieldsets = super().get_fieldsets(*args, **kwargs)
        default_fieldset = dict(fieldsets).get(None, None)
        if not default_fieldset:
            return fieldsets
        fields = default_fieldset['fields'].copy()
        if all(f in fields for f in ('art', 'zusammenfassung')):
            art = fields.index('art')
            zusammenfassung = fields.index('zusammenfassung')
            fields[art], fields[zusammenfassung] = fields[zusammenfassung], fields[art]
            default_fieldset['fields'] = fields
        return fieldsets


@admin.register(_models.Kalender, site=miz_site)
class KalenderAdmin(BaseBrochureAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through
    class JahrInLine(BaseTabularInline):  # noqa
        model = _models.BrochureYear
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Kalender.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Kalender.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']
    class URLInLine(BaseTabularInline):  # noqa
        model = _models.BrochureURL

    inlines = [
        URLInLine, JahrInLine, GenreInLine, SpielortInLine,
        VeranstaltungInLine, BestandInLine]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'genre', 'spielort', 'veranstaltung',
            'jahre__jahr__range'
        ],
        'forwards': {'ausgabe': 'ausgabe__magazin'},
        'labels': {'jahre__jahr__range': 'Jahr'},
        'tabular': ['ausgabe', 'spielort', 'veranstaltung']
    }
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Foto, site=miz_site)
class FotoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Foto.genre.through
    class SchlInLine(BaseSchlagwortInline):  # noqa
        model = _models.Foto.schlagwort.through
    class PersonInLine(BaseTabularInline):  # noqa
        model = _models.Foto.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseTabularInline):  # noqa
        model = _models.Foto.musiker.through
        verbose_model = _models.Musiker
        tabular_autocomplete = ['musiker']
    class BandInLine(BaseTabularInline):  # noqa
        model = _models.Foto.band.through
        verbose_model = _models.Band
        tabular_autocomplete = ['band']
    class OrtInLine(BaseTabularInline):  # noqa
        model = _models.Foto.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):  # noqa
        model = _models.Foto.spielort.through
        verbose_model = _models.Spielort
        tabular_autocomplete = ['veranstaltung']
    class VeranstaltungInLine(BaseTabularInline):  # noqa
        model = _models.Foto.veranstaltung.through
        verbose_model = _models.Veranstaltung
        tabular_autocomplete = ['veranstaltung']

    collapse_all = True
    form = _forms.FotoForm
    index_category = 'Archivgut'
    list_display = ['titel', 'foto_id', 'size', 'typ', 'datum_localized', 'schlagwort_list']
    readonly_fields = ['foto_id']
    save_on_top = True
    ordering = ['titel', 'datum']

    fields = [
        'titel', 'foto_id', 'size', 'typ', 'farbe', 'datum', 'reihe',
        'owner', 'beschreibung', 'bemerkungen'
    ]
    inlines = [
        SchlInLine, GenreInLine, MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'reihe', 'datum__range'
        ],
        'labels': {'reihe': 'Bildreihe'},
        'tabular': ['musiker', 'band', 'spielort', 'veranstaltung'],
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self) -> Dict[str, ArrayAgg]:
        return {
            'schlagwort_list':
                ArrayAgg('schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort')
        }

    def foto_id(self, obj: _models.Foto) -> str:
        """Return the id of the object, padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return str(obj.pk).zfill(6)
    foto_id.short_description = 'Foto ID'  # type: ignore[attr-defined]  # noqa
    foto_id.admin_order_field = 'id'  # type: ignore[attr-defined]  # noqa

    def datum_localized(self, obj: _models.Foto) -> str:
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'  # type: ignore[attr-defined]  # noqa
    datum_localized.admin_order_field = 'datum'  # type: ignore[attr-defined]  # noqa

    def schlagwort_list(self, obj: _models.Foto) -> str:
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display()  # added by annotations  # noqa
    schlagwort_list.short_description = 'Schlagworte'  # type: ignore[attr-defined]  # noqa
    schlagwort_list.admin_order_field = 'schlagwort_list'  # type: ignore[attr-defined]  # noqa


@admin.register(
    _models.Monat, _models.Lagerort, _models.Geber, _models.Plattenfirma,
    _models.Provenienz, _models.Schriftenreihe, _models.Bildreihe, _models.Veranstaltungsreihe,
    _models.VideoMedium, _models.AudioMedium,
    site=miz_site
)
class HiddenFromIndex(MIZModelAdmin):
    superuser_only = True


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
    ) -> FormField:
        """
        Get a form field for a ManyToManyField. If it's the formfield for
        Permissions, adjust the choices to include the models' class names.
        """
        # noinspection PyUnresolvedReferences
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
                choices.append((
                    perm.pk,
                    "%s | %s | %s" % (perm.content_type.app_label, object_name, perm.name,)
                ))
            formfield.choices = choices
        return formfield


@admin.register(Group, site=miz_site)
class MIZGroupAdmin(AuthAdminMixin, GroupAdmin):
    pass


@admin.register(User, site=miz_site)
class MIZUserAdmin(AuthAdminMixin, UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'activity'
    )

    def get_queryset(self, request: HttpRequest):
        queryset = super().get_queryset(request)
        # Note that the order_by and values calls are required:
        # see django docs expressions/#using-aggregates-within-a-subquery-expression
        recent_logs = LogEntry.objects.filter(
            user_id=OuterRef('id'),
            action_time__date__gt=datetime.now() - timedelta(days=32)
        ) .order_by().values('user_id')
        subquery = Subquery(
            recent_logs.annotate(c=Count('*')).values('c'), output_field=IntegerField()
        )
        return queryset.annotate(activity=Coalesce(subquery, Value(0)))

    def activity(self, user: User) -> int:
        """Return the total amount of the recent changes made by this user."""
        # noinspection PyUnresolvedReferences
        return user.activity or 0
    activity.short_description = 'Aktivität letzte 30 Tage'  # type: ignore[attr-defined]
    activity.admin_order_field = 'activity'  # type: ignore[attr-defined]
    pass


@admin.register(LogEntry, site=miz_site)
class MIZLogEntryAdmin(MIZAdminSearchFormMixin, LogEntryAdmin):
    fields = (
        'action_time', 'user', 'content_type', 'object', 'object_id',
        'action_flag', 'change_message_verbose', 'change_message_raw'
    )
    readonly_fields = ('object', 'change_message_verbose', 'change_message_raw')

    list_display = (
        'action_time', 'user', 'action_message', 'content_type', 'object_link',
    )
    list_filter = ()
    search_form_kwargs = {
        'fields': ('user', 'content_type', 'action_flag'),
        'widgets': {
            'user': autocomplete.ModelSelect2(url='autocomplete_user'),
            'content_type': autocomplete.ModelSelect2(url='autocomplete_ct'),
        }
    }

    def object(self, obj):
        return self.object_link(obj)

    def change_message_verbose(self, obj):
        return obj.get_change_message()
    change_message_verbose.short_description = 'Änderungsmeldung'  # type: ignore[attr-defined]

    def change_message_raw(self, obj):
        return obj.change_message
    change_message_raw.short_description = 'Datenbank-Darstellung'  # type: ignore[attr-defined]
