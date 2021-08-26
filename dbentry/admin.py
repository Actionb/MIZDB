from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User, Permission
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import transaction
from django.db.models import Count, Min, Subquery, OuterRef, Func, Value, Exists

import dbentry.models as _models
import dbentry.m2m as _m2m
import dbentry.actions.actions as _actions
from dbentry.ac.widgets import make_widget
from dbentry.base.admin import (
    MIZModelAdmin, BaseAliasInline, BaseAusgabeInline, BaseGenreInline,
    BaseSchlagwortInline, BaseStackedInline, BaseTabularInline, BaseOrtInLine
)
from dbentry.forms import (
    ArtikelForm, AutorForm, BuchForm, BrochureForm, AudioForm,
    PlakatForm, MusikerForm, BandForm, VideoForm, FotoForm, PersonForm
)
from dbentry.sites import miz_site
from dbentry.utils import concat_limit, copy_related_set
from dbentry.utils.admin import get_obj_link, log_change
# TODO: add admindocs
# (https://docs.djangoproject.com/en/2.2/ref/contrib/admin/admindocs/)


class BestandInLine(BaseTabularInline):
    model = _models.Bestand
    # This allows inlines.js to copy the last selected bestand to a new row.
    classes = ['copylast']
    fields = ['signatur', 'lagerort', 'provenienz']
    readonly_fields = ['signatur']
    verbose_name = _models.Bestand._meta.verbose_name
    verbose_name_plural = _models.Bestand._meta.verbose_name_plural


@admin.register(_models.Audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Audio.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Audio.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.Audio.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.Audio.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.Audio.band.through
        verbose_model = _models.Band
    class SpielortInLine(BaseTabularInline):
        model = _models.Audio.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Audio.veranstaltung.through
        verbose_model = _models.Veranstaltung
    class OrtInLine(BaseTabularInline):
        model = _models.Audio.ort.through
        verbose_model = _models.Ort
    class PlattenInLine(BaseTabularInline):
        model = _models.Audio.plattenfirma.through
        verbose_model = _models.Plattenfirma
    class AusgabeInLine(BaseAusgabeInline):
        model = _models.Ausgabe.audio.through
    class DateiInLine(BaseTabularInline):
        model = _m2m.m2m_datei_quelle
        fields = ['datei']
        verbose_model = _models.Datei

    collapse_all = True
    form = AudioForm
    index_category = 'Archivgut'
    save_on_top = True
    list_display = ['titel', 'jahr', 'medium', 'kuenstler_string']
    list_select_related = ['medium']
    ordering = ['titel', 'jahr', 'medium']

    fieldsets = [
        (None, {'fields': [
                'titel', 'tracks', 'laufzeit', 'jahr', 'land_pressung', 'original', 'quelle',
                ('medium', 'medium_qty'), 'plattennummer', 'beschreibung', 'bemerkungen'
        ]}),
        ('Discogs', {
            'fields': ['release_id', 'discogs_url'], 'classes': ['collapse', 'collapsed']}
        ),
    ]
    inlines = [
        MusikerInLine, BandInLine,
        SchlInLine, GenreInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, PlattenInLine,
        AusgabeInLine, DateiInLine,
        BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'plattenfirma', 'medium', 'release_id',
            'land_pressung'
        ],
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self):
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj):
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'


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
        verbose_name_plural = 'erschienen im Jahr'
    class AudioInLine(BaseTabularInline):
        model = _models.Ausgabe.audio.through
        verbose_model = _models.Audio
    class VideoInLine(BaseTabularInline):
        model = _models.Ausgabe.video.through
        verbose_model = _models.Video

    index_category = 'Archivgut'
    inlines = [NumInLine, MonatInLine, LNumInLine, JahrInLine, AudioInLine, VideoInLine, BestandInLine]
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

    def get_changelist(self, request, **kwargs):
        from .changelist import AusgabeChangeList
        return AusgabeChangeList

    def ausgabe_name(self, obj):
        return obj._name
    ausgabe_name.short_description = 'Ausgabe'
    ausgabe_name.admin_order_field = '_name'

    def magazin_name(self, obj):
        return obj.magazin.magazin_name
    magazin_name.short_description = 'Magazin'
    magazin_name.admin_order_field = 'magazin__magazin_name'

    def get_result_list_annotations(self):
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
                    Value(', '), Value(self.get_empty_value_display()), function='array_to_string'
                )
            )
            .values('x')
        )
        return {
            'jahr_string': Func(
                ArrayAgg('ausgabejahr__jahr', distinct=True, ordering='ausgabejahr__jahr'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string'
            ),
            'num_string': Func(
                ArrayAgg('ausgabenum__num', distinct=True, ordering='ausgabenum__num'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string'
            ),
            'lnum_string': Func(
                ArrayAgg('ausgabelnum__lnum', distinct=True, ordering='ausgabelnum__lnum'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string'
            ),
            'monat_string': Subquery(subquery),
            'anz_artikel': Count('artikel', distinct=True)
        }

    def anz_artikel(self, obj):
        return obj.anz_artikel
    anz_artikel.short_description = 'Anz. Artikel'
    anz_artikel.admin_order_field = 'anz_artikel'

    def jahr_string(self, obj):
        return obj.jahr_string
    jahr_string.short_description = 'Jahre'
    jahr_string.admin_order_field = 'jahr_string'

    def num_string(self, obj):
        return obj.num_string
    num_string.short_description = 'Nummer'
    num_string.admin_order_field = 'num_string'

    def lnum_string(self, obj):
        return obj.lnum_string
    lnum_string.short_description = 'lfd. Nummer'
    lnum_string.admin_order_field = 'lnum_string'

    def monat_string(self, obj):
        return obj.monat_string
    monat_string.short_description = 'Monate'
    monat_string.admin_order_field = 'monat_string'

    def _change_status(self, request, queryset, status):
        with transaction.atomic():
            queryset.update(status=status, _changed_flag=False)
        try:
            with transaction.atomic():
                for obj in queryset:
                    log_change(request.user.pk, obj, fields=['status'])
        except Exception as e:
            message_text = (
                "Fehler beim Erstellen der LogEntry Objekte: \n"
                "%(error_class)s: %(error_txt)s" % {
                    'error_class': e.__class__.__name__, 'error_txt': e.args[0]}
            )
            self.message_user(request, message_text, 'ERROR')

    def change_status_unbearbeitet(self, request, queryset):
        self._change_status(request, queryset, _models.Ausgabe.UNBEARBEITET)
    change_status_unbearbeitet.allowed_permissions = ['change']
    change_status_unbearbeitet.short_description = 'Status ändern: unbearbeitet'

    def change_status_inbearbeitung(self, request, queryset):
        self._change_status(request, queryset, _models.Ausgabe.INBEARBEITUNG)
    change_status_inbearbeitung.allowed_permissions = ['change']
    change_status_inbearbeitung.short_description = 'Status ändern: in Bearbeitung'

    def change_status_abgeschlossen(self, request, queryset):
        self._change_status(request, queryset, _models.Ausgabe.ABGESCHLOSSEN)
    change_status_abgeschlossen.allowed_permissions = ['change']
    change_status_abgeschlossen.short_description = 'Status ändern: abgeschlossen'

    def has_moveto_brochure_permission(self, request):
        from django.contrib.auth import get_permission_codename
        perms = []
        for name, opts in [('delete', _models.Ausgabe._meta), ('add', _models.BaseBrochure._meta)]:
            perms.append("%s.%s" % (opts.app_label, get_permission_codename(name, opts)))
        return request.user.has_perms(perms)


@admin.register(_models.Autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = _models.Autor.magazin.through
        verbose_model = _models.Magazin
        extra = 1
    class URLInLine(BaseTabularInline):
        model = _models.AutorURL

    form = AutorForm
    index_category = 'Stammdaten'
    inlines = [URLInLine, MagazinInLine]
    list_display = ['autor_name', 'person', 'kuerzel', 'magazin_string']
    list_select_related = ['person']
    search_form_kwargs = {'fields': ['magazin', 'person']}
    ordering = ['_name']

    def get_result_list_annotations(self):
        return {
            'magazin_list': ArrayAgg(
                'magazin__magazin_name', distinct=True, ordering='magazin__magazin_name')
        }

    def autor_name(self, obj):
        return obj._name
    autor_name.short_description = 'Autor'
    autor_name.admin_order_field = '_name'

    def magazin_string(self, obj):
        return concat_limit(obj.magazin_list) or self.get_empty_value_display()
    magazin_string.short_description = 'Magazin(e)'
    magazin_string.admin_order_field = 'magazin_list'


@admin.register(_models.Artikel, site=miz_site)
class ArtikelAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Artikel.genre.through
    class SchlInLine(BaseSchlagwortInline):
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
    class BandInLine(BaseTabularInline):
        model = _models.Artikel.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Artikel.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Artikel.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Artikel.veranstaltung.through
        verbose_model = _models.Veranstaltung

    form = ArtikelForm
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
        'forwards': {'ausgabe': 'ausgabe__magazin'}
    }

    def get_result_list_annotations(self):
        return {
            'schlagwort_list': ArrayAgg(
                'schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort'),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def ausgabe_name(self, obj):
        return obj.ausgabe._name
    ausgabe_name.short_description = 'Ausgabe'
    ausgabe_name.admin_order_field = 'ausgabe___name'

    def zusammenfassung_string(self, obj):
        if not obj.zusammenfassung:
            return self.get_empty_value_display()
        return concat_limit(obj.zusammenfassung.split(), sep=" ", width=100)
    zusammenfassung_string.short_description = 'Zusammenfassung'
    zusammenfassung_string.admin_order_field = 'zusammenfassung'

    def artikel_magazin(self, obj):
        return obj.ausgabe.magazin.magazin_name
    artikel_magazin.short_description = 'Magazin'
    artikel_magazin.admin_order_field = 'ausgabe__magazin__magazin_name'

    def schlagwort_string(self, obj):
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display()
    schlagwort_string.short_description = 'Schlagwörter'
    schlagwort_string.admin_order_field = 'schlagwort_list'

    def kuenstler_string(self, obj):
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'


@admin.register(_models.Band, site=miz_site)
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Band.genre.through
    class MusikerInLine(BaseTabularInline):
        model = _models.Band.musiker.through
        verbose_name = 'Band-Mitglied'
        verbose_name_plural = 'Band-Mitglieder'
    class AliasInLine(BaseAliasInline):
        model = _models.BandAlias
    class OrtInLine(BaseOrtInLine):
        model = _models.Band.orte.through
    class URLInLine(BaseTabularInline):
        model = _models.BandURL

    form = BandForm
    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, AliasInLine, MusikerInLine, OrtInLine]
    list_display = ['band_name', 'genre_string', 'musiker_string', 'orte_string']
    save_on_top = True
    ordering = ['band_name']

    search_form_kwargs = {
        'fields': ['musiker', 'genre', 'orte__land', 'orte'],
        'labels': {'musiker': 'Mitglied'}
    }

    def get_result_list_annotations(self):
        return {
            'genre_list': ArrayAgg('genre__genre', distinct=True, ordering='genre__genre'),
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'alias_list': ArrayAgg(
                'bandalias__alias', distinct=True, ordering='bandalias__alias'),
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name')
        }

    def genre_string(self, obj):
        return concat_limit(obj.genre_list) or self.get_empty_value_display()
    genre_string.short_description = 'Genres'
    genre_string.admin_order_field = 'genre_list'

    def musiker_string(self, obj):
        return concat_limit(obj.musiker_list) or self.get_empty_value_display()
    musiker_string.short_description = 'Mitglieder'
    musiker_string.admin_order_field = 'musiker_list'

    def alias_string(self, obj):
        return concat_limit(obj.alias_list) or self.get_empty_value_display()
    alias_string.short_description = 'Aliase'
    alias_string.admin_order_field = 'alias_list'

    def orte_string(self, obj):
        return concat_limit(obj.orte_list) or self.get_empty_value_display()
    orte_string.short_description = 'Orte'
    orte_string.admin_order_field = 'orte_list'


@admin.register(_models.Plakat, site=miz_site)
class PlakatAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Plakat.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Plakat.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.Plakat.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseTabularInline):
        model = _models.Plakat.musiker.through
        verbose_model = _models.Musiker
    class BandInLine(BaseTabularInline):
        model = _models.Plakat.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Plakat.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Plakat.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Plakat.veranstaltung.through
        verbose_model = _models.Veranstaltung

    collapse_all = True
    form = PlakatForm
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
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self):
        return {
            'veranstaltung_list':
                ArrayAgg('veranstaltung__name', distinct=True, ordering='veranstaltung__name')
        }

    def datum_localized(self, obj):
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'
    datum_localized.admin_order_field = 'datum'

    def veranstaltung_string(self, obj):
        return concat_limit(obj.veranstaltung_list) or self.get_empty_value_display()
    veranstaltung_string.short_description = 'Veranstaltungen'
    veranstaltung_string.admin_order_field = 'veranstaltung_list'

    def get_fields(self, request, obj=None):
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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        self._copy_related(request, form.instance)

    def _copy_related(self, request, obj):
        """Copy Band and Musiker instances of Veranstaltung to this object."""
        if 'copy_related' in request.POST:
            copy_related_set(
                request, obj, 'veranstaltung__band', 'veranstaltung__musiker')

    def plakat_id(self, obj):
        """ID of this instance, with a prefixed 'P' and padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return "P" + str(obj.pk).zfill(6)
    plakat_id.short_description = 'Plakat ID'
    plakat_id.admin_order_field = 'id'


@admin.register(_models.Buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Buch.genre.through
    class SchlInLine(BaseSchlagwortInline):
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
    class BandInLine(BaseTabularInline):
        model = _models.Buch.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Buch.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Buch.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Buch.veranstaltung.through
        verbose_model = _models.Veranstaltung
    class HerausgeberInLine(BaseTabularInline):
        model = _models.Buch.herausgeber.through
        verbose_model = _models.Herausgeber
    class VerlagInLine(BaseTabularInline):
        model = _models.Buch.verlag.through
        verbose_model = _models.Verlag

    collapse_all = True
    # TODO: Semantik: Einzelbänder/Aufsätze: Teile eines Buchbandes
    crosslink_labels = {'buch': 'Aufsätze'}
    form = BuchForm
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
        # 'autor' help_text refers to quick item creation which is not allowed
        # in search forms - disable the help_text.
        'help_texts': {'autor': None}
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self):
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

    def autoren_string(self, obj):
        return concat_limit(obj.autor_list) or self.get_empty_value_display()
    autoren_string.short_description = 'Autoren'
    autoren_string.admin_order_field = 'autor_list'

    def schlagwort_string(self, obj):
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display()
    schlagwort_string.short_description = 'Schlagwörter'
    schlagwort_string.admin_order_field = 'schlagwort_list'

    def genre_string(self, obj):
        return concat_limit(obj.genre_list) or self.get_empty_value_display()
    genre_string.short_description = 'Genres'
    genre_string.admin_order_field = 'genre_list'

    def kuenstler_string(self, obj):
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'


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
    search_fields = ['genre', 'genrealias__alias']
    ordering = ['genre']

    def get_result_list_annotations(self):
        return {
            'alias_list': ArrayAgg('genrealias__alias', ordering='genrealias__alias')
        }

    def alias_string(self, obj):
        return concat_limit(obj.alias_list) or self.get_empty_value_display()
    alias_string.short_description = 'Aliase'


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

    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, VerlagInLine, HerausgeberInLine, OrtInLine]
    list_display = ['magazin_name', 'short_beschreibung', 'orte_string', 'anz_ausgaben']
    ordering = ['magazin_name']

    search_form_kwargs = {
        'fields': ['verlag', 'herausgeber', 'orte', 'genre', 'issn', 'fanzine'],
    }

    def get_result_list_annotations(self):
        return {
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name'),
            'anz_ausgaben': Count('ausgabe', distinct=True)
        }

    def anz_ausgaben(self, obj):
        return obj.anz_ausgaben
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    anz_ausgaben.admin_order_field = 'anz_ausgaben'

    def orte_string(self, obj):
        return concat_limit(obj.orte_list) or self.get_empty_value_display()
    orte_string.short_description = 'Orte'
    orte_string.admin_order_field = 'orte_list'

    def short_beschreibung(self, obj):
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")
    short_beschreibung.short_description = 'Beschreibung'
    short_beschreibung.admin_order_field = 'beschreibung'

    def get_exclude(self, request, obj=None):
        """
        Exclude 'ausgaben_merkmal' from the add/change page if the current
        user is not a superuser.
        """
        exclude = super().get_exclude(request, obj) or []
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
    class BandInLine(BaseTabularInline):
        model = _models.Band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
    class AliasInLine(BaseAliasInline):
        model = _models.MusikerAlias
    class InstrInLine(BaseTabularInline):
        model = _models.Musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    class OrtInLine(BaseOrtInLine):
        model = _models.Musiker.orte.through
    class URLInLine(BaseTabularInline):
        model = _models.MusikerURL

    form = MusikerForm
    fields = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, AliasInLine, BandInLine, OrtInLine, InstrInLine]
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'orte_string']
    save_on_top = True
    search_form_kwargs = {'fields': ['person', 'genre', 'instrument', 'orte__land', 'orte']}
    ordering = ['kuenstler_name']

    def get_result_list_annotations(self):
        return {
            'band_list': ArrayAgg('band__band_name', distinct=True, ordering='band__band_name'),
            'genre_list': ArrayAgg('genre__genre', distinct=True, ordering='genre__genre'),
            'orte_list': ArrayAgg('orte___name', distinct=True, ordering='orte___name')
        }

    def band_string(self, obj):
        return concat_limit(obj.band_list) or self.get_empty_value_display()
    band_string.short_description = 'Bands'
    band_string.admin_order_field = 'band_list'

    def genre_string(self, obj):
        return concat_limit(obj.genre_list) or self.get_empty_value_display()
    genre_string.short_description = 'Genres'
    genre_string.admin_order_field = 'genre_list'

    def orte_string(self, obj):
        return concat_limit(obj.orte_list) or self.get_empty_value_display()
    orte_string.short_description = 'Orte'
    orte_string.admin_order_field = 'orte_list'


@admin.register(_models.Person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = _models.Person.orte.through
    class URLInLine(BaseTabularInline):
        model = _models.PersonURL

    index_category = 'Stammdaten'
    inlines = [URLInLine, OrtInLine]
    list_display = ('vorname', 'nachname', 'orte_string', 'is_musiker', 'is_autor')
    list_display_links = ['vorname', 'nachname']
    ordering = ['nachname', 'vorname']
    form = PersonForm

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

    def get_result_list_annotations(self):
        return {
            'is_musiker': Exists(
                _models.Musiker.objects.only('id').filter(person_id=OuterRef('id'))),
            'is_autor': Exists(
                _models.Autor.objects.only('id').filter(person_id=OuterRef('id'))),
            'orte_list': ArrayAgg(
                'orte___name', distinct=True, ordering='orte___name')
        }

    def is_musiker(self, obj):
        return obj.is_musiker
    is_musiker.short_description = 'Ist Musiker'
    is_musiker.boolean = True

    def is_autor(self, obj):
        return obj.is_autor
    is_autor.short_description = 'Ist Autor'
    is_autor.boolean = True

    def orte_string(self, obj):
        return concat_limit(obj.orte_list) or self.get_empty_value_display()
    orte_string.short_description = 'Orte'
    orte_string.admin_order_field = 'orte_list'


@admin.register(_models.Schlagwort, site=miz_site)
class SchlagwortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SchlagwortAlias
        extra = 1

    index_category = 'Stammdaten'
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string']
    search_fields = ['schlagwort', 'schlagwortalias__alias']
    ordering = ['schlagwort']

    def get_result_list_annotations(self):
        return {
            'alias_list': ArrayAgg('schlagwortalias__alias', ordering='schlagwortalias__alias')
        }

    def alias_string(self, obj):
        return concat_limit(obj.alias_list) or self.get_empty_value_display()
    alias_string.short_description = 'Aliase'
    alias_string.admin_order_field = 'alias_list'


@admin.register(_models.Spielort, site=miz_site)
class SpielortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.SpielortAlias
    class URLInLine(BaseTabularInline):
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
    class BandInLine(BaseTabularInline):
        model = _models.Veranstaltung.band.through
        verbose_model = _models.Band
    class PersonInLine(BaseTabularInline):
        model = _models.Veranstaltung.person.through
        verbose_model = _models.Person
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Veranstaltung.schlagwort.through
    class MusikerInLine(BaseTabularInline):
        model = _models.Veranstaltung.musiker.through
        verbose_model = _models.Musiker
    class AliasInLine(BaseAliasInline):
        model = _models.VeranstaltungAlias
    class URLInLine(BaseTabularInline):
        model = _models.VeranstaltungURL

    collapse_all = True
    inlines = [URLInLine, AliasInLine, MusikerInLine, BandInLine, SchlInLine, GenreInLine, PersonInLine]
    list_display = ['name', 'datum_localized', 'spielort', 'kuenstler_string']
    save_on_top = True
    ordering = ['name', 'spielort', 'datum']
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'person', 'spielort',
            'reihe', 'datum__range'
        ]
    }

    def get_result_list_annotations(self):
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj):
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'

    def datum_localized(self, obj):
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'
    datum_localized.admin_order_field = 'datum'


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
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Video.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.Video.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.Video.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.Video.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Video.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Video.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Video.veranstaltung.through
        verbose_model = _models.Veranstaltung
    class AusgabeInLine(BaseAusgabeInline):
        model = _models.Ausgabe.video.through
    class DateiInLine(BaseTabularInline):
        model = _m2m.m2m_datei_quelle
        fields = ['datei']
        verbose_model = _models.Datei

    form = VideoForm
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
        (None, {'fields': [
                'titel', 'laufzeit', 'jahr', 'original', 'quelle', ('medium', 'medium_qty'),
                'beschreibung', 'bemerkungen'
        ]}),
        ('Discogs', {'fields': ['release_id', 'discogs_url'], 'classes': ['collapse', 'collapsed']}),
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'schlagwort', 'genre', 'ort', 'spielort',
            'veranstaltung', 'person', 'medium', 'release_id'
        ],
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self):
        return {
            'musiker_list': ArrayAgg(
                'musiker__kuenstler_name', distinct=True, ordering='musiker__kuenstler_name'),
            'band_list': ArrayAgg(
                'band__band_name', distinct=True, ordering='band__band_name')
        }

    def kuenstler_string(self, obj):
        return concat_limit(obj.band_list + obj.musiker_list) or self.get_empty_value_display()
    kuenstler_string.short_description = 'Künstler'


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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field == self.opts.get_field('bland'):
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

    def get_queryset(self, request, **kwargs):
        self.request = request  # save the request for bestand_link()
        return super().get_queryset(request, **kwargs)

    def bestand_class(self, obj):
        if obj.bestand_object:
            return obj.bestand_object._meta.verbose_name
        return ''
    bestand_class.short_description = 'Art'

    def bestand_link(self, obj):
        if obj.bestand_object:
            return get_obj_link(obj.bestand_object, self.request.user, blank=True)
        return ''
    bestand_link.short_description = 'Link'

    def _check_search_form_fields(self, **kwargs):
        # Ignore the search form fields check for BestandAdmin.
        return []


@admin.register(_models.Datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Datei.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Datei.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.Datei.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.Datei.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.Datei.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Datei.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Datei.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Datei.veranstaltung.through
        verbose_model = _models.Veranstaltung
    class QuelleInLine(BaseStackedInline):
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
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear
    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    form = BrochureForm
    index_category = 'Archivgut'
    inlines = [URLInLine, JahrInLine, GenreInLine, BestandInLine]
    list_display = ['titel', 'zusammenfassung', 'jahr_string']
    search_form_kwargs = {
        'fields': ['ausgabe__magazin', 'ausgabe', 'genre', 'jahre__jahr__range'],
        'labels': {'jahre__jahr__range': 'Jahr'}
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_fieldsets(self, request, obj=None):
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

    def get_ordering(self, request):
        return ['titel', 'jahr_min', 'zusammenfassung']

    def get_result_list_annotations(self):
        return {
            'jahr_string': Func(
                ArrayAgg('jahre__jahr', distinct=True, ordering='jahre__jahr'),
                Value(', '), Value(self.get_empty_value_display()), function='array_to_string'
            ),
            'jahr_min': Min('jahre__jahr')
        }

    def jahr_string(self, obj):
        return obj.jahr_string
    jahr_string.short_description = 'Jahre'
    jahr_string.admin_order_field = 'jahr_min'


@admin.register(_models.Brochure, site=miz_site)
class BrochureAdmin(BaseBrochureAdmin):
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Brochure.schlagwort.through
    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    inlines = [URLInLine, JahrInLine, GenreInLine, SchlInLine, BestandInLine]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'genre', 'schlagwort',
            'jahre__jahr__range'
        ],
        'labels': {'jahre__jahr__range': 'Jahr'}
    }
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Katalog, site=miz_site)
class KatalogAdmin(BaseBrochureAdmin):

    list_display = ['titel', 'zusammenfassung', 'art', 'jahr_string']
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_fieldsets(self, *args, **kwargs):
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
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear
    class SpielortInLine(BaseTabularInline):
        model = _models.Kalender.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Kalender.veranstaltung.through
        verbose_model = _models.Veranstaltung
    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    inlines = [
        URLInLine, JahrInLine, GenreInLine, SpielortInLine,
        VeranstaltungInLine, BestandInLine]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'genre', 'spielort', 'veranstaltung',
            'jahre__jahr__range'
        ],
        'labels': {'jahre__jahr__range': 'Jahr'}
    }
    actions = [_actions.merge_records, _actions.change_bestand]


@admin.register(_models.Foto, site=miz_site)
class FotoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Foto.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.Foto.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.Foto.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseTabularInline):
        model = _models.Foto.musiker.through
        verbose_model = _models.Musiker
    class BandInLine(BaseTabularInline):
        model = _models.Foto.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.Foto.ort.through
        verbose_model = _models.Ort
    class SpielortInLine(BaseTabularInline):
        model = _models.Foto.spielort.through
        verbose_model = _models.Spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Foto.veranstaltung.through
        verbose_model = _models.Veranstaltung

    collapse_all = True
    form = FotoForm
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
        'labels': {'reihe': 'Bildreihe'}
    }
    actions = [_actions.merge_records, _actions.change_bestand]

    def get_result_list_annotations(self):
        return {
            'schlagwort_list':
                ArrayAgg('schlagwort__schlagwort', distinct=True, ordering='schlagwort__schlagwort')
        }

    def foto_id(self, obj):
        """Return the id of the object, padded with zeros."""
        if not obj.pk:
            return self.get_empty_value_display()
        return str(obj.pk).zfill(6)
    foto_id.short_description = 'Foto ID'
    foto_id.admin_order_field = 'id'

    def datum_localized(self, obj):
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'
    datum_localized.admin_order_field = 'datum'

    def schlagwort_list(self, obj):
        return concat_limit(obj.schlagwort_list) or self.get_empty_value_display()
    schlagwort_list.short_description = 'Schlagworte'
    schlagwort_list.admin_order_field = 'schlagwort_list'


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

    By default the choice's names contain the verbose_name of a model, which may
    not be unique enough to be able to differentiate between different
    permissions.
    """

    def formfield_for_manytomany(self, db_field, request=None, **kwargs):
        formfield = super().formfield_for_manytomany(db_field, request=request, **kwargs)
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
    pass
