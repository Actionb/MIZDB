from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.db.models import Count, Min

import DBentry.models as _models
import DBentry.m2m as _m2m
import DBentry.actions as _actions
from DBentry.ac.widgets import make_widget
from DBentry.base.admin import (
    MIZModelAdmin, BaseAliasInline, BaseAusgabeInline, BaseGenreInline,
    BaseSchlagwortInline, BaseStackedInline, BaseTabularInline, BaseOrtInLine
)
from DBentry.forms import (
    ArtikelForm, AutorForm, BuchForm, BrochureForm, AudioForm,
    BildmaterialForm, MusikerForm, BandForm
)
from DBentry.sites import miz_site
from DBentry.utils import concat_limit, copy_related_set


class BestandInLine(BaseTabularInline):
    model = _models.bestand
    # This allows inlines.js to copy the last selected bestand to a new row.
    classes = ['copylast']
    fields = ['signatur', 'lagerort', 'provenienz']
    readonly_fields = ['signatur']
    verbose_name = _models.bestand._meta.verbose_name
    verbose_name_plural = _models.bestand._meta.verbose_name_plural


@admin.register(_models.audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.audio.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.audio.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.audio.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.audio.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.audio.band.through
        verbose_model = _models.Band
    class SpielortInLine(BaseTabularInline):
        model = _models.audio.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.audio.veranstaltung.through
        verbose_model = _models.veranstaltung
    class FormatInLine(BaseStackedInline):
        model = _models.Format
        extra = 0
        filter_horizontal = ['tag']
        fieldsets = [
            (None, {'fields': ['anzahl', 'format_typ', 'format_size', 'catalog_nr']}),
            ('Tags', {'fields': ['tag'], 'classes': ['collapse', 'collapsed']}),
            ('Bemerkungen', {'fields': ['bemerkungen'], 'classes': ['collapse', 'collapsed']})
        ]
    class OrtInLine(BaseTabularInline):
        model = _models.audio.ort.through
        verbose_model = _models.ort
    class PlattenInLine(BaseTabularInline):
        model = _models.audio.plattenfirma.through
        verbose_model = _models.plattenfirma
    class AusgabeInLine(BaseAusgabeInline):
        model = _models.Ausgabe.audio.through
    class DateiInLine(BaseTabularInline):
        model = _m2m.m2m_datei_quelle
        fields = ['datei']
        verbose_model = _models.datei

    collapse_all = True
    form = AudioForm
    index_category = 'Archivgut'
    save_on_top = True
    list_display = ['__str__', 'formate_string', 'kuenstler_string']
    list_prefetch_related = ['band', 'musiker', 'format_set']

    fieldsets = [
        (None, {'fields':
                ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle',
                'beschreibung', 'bemerkungen']
        }),
        ('Discogs', {'fields': ['release_id', 'discogs_url'], 'classes': ['collapse', 'collapsed']}),
    ]
    inlines = [
        GenreInLine, SchlInLine,
        MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, FormatInLine, PlattenInLine,
        AusgabeInLine, DateiInLine,
        BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'musiker', 'band', 'person', 'genre', 'schlagwort',
            'ort', 'spielort', 'veranstaltung', 'plattenfirma',
            'format__format_size', 'format__format_typ', 'format__tag',
            'release_id', 'id__in'
        ],
        'labels': {'format__tag': 'Tags'}
    }

    def kuenstler_string(self, obj):
        return concat_limit(list(obj.band.all()) + list(obj.musiker.all()))
    kuenstler_string.short_description = 'Künstler'

    def formate_string(self, obj):
        return concat_limit(list(obj.format_set.all()))
    formate_string.short_description = 'Format'


@admin.register(_models.Ausgabe, site=miz_site)
class AusgabenAdmin(MIZModelAdmin):
    class NumInLine(BaseTabularInline):
        model = _models.AusgabeNum
        extra = 0
    class MonatInLine(BaseTabularInline):
        model = _models.AusgabeMonat
        verbose_model = _models.monat
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

    index_category = 'Archivgut'
    inlines = [NumInLine, MonatInLine, LNumInLine, JahrInLine, AudioInLine, BestandInLine]
    list_prefetch_related = [
        'ausgabejahr_set', 'ausgabenum_set', 'ausgabelnum_set', 'ausgabemonat_set']

    fields = [
        'magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang',
        'beschreibung', 'bemerkungen'
    ]
    list_display = (
        '__str__', 'num_string', 'lnum_string', 'monat_string', 'jahr_string',
        'jahrgang', 'magazin', 'e_datum', 'anz_artikel', 'status'
    )
    search_form_kwargs = {
        'fields': [
            'magazin', 'status', 'ausgabejahr__jahr__range', 'ausgabenum__num__range',
            'ausgabelnum__lnum__range', 'ausgabemonat__monat__ordinal__range',
            'jahrgang', 'sonderausgabe', 'audio', 'id__in'
        ],
        'labels': {
            'ausgabejahr__jahr__range': 'Jahr',
            'ausgabenum__num__range': 'Nummer',
            'ausgabelnum__lnum__range': 'Lfd. Nummer',
            'ausgabemonat__monat__ordinal__range': 'Monatsnummer',
            'audio': 'Audio (Beilagen)'
        }
    }

    actions = [
        _actions.merge_records, _actions.bulk_jg, _actions.add_bestand,
        _actions.moveto_brochure
    ]

    def get_changelist(self, request, **kwargs):
        from .changelist import AusgabeChangeList
        return AusgabeChangeList

    def anz_artikel(self, obj):
        return obj.anz_artikel
    anz_artikel.short_description = 'Anz. Artikel'
    anz_artikel.admin_order_field = 'anz_artikel'
    anz_artikel.annotation = Count('artikel', distinct=True)

    def jahr_string(self, obj):
        return concat_limit(obj.ausgabejahr_set.all())
    jahr_string.short_description = 'Jahre'

    def num_string(self, obj):
        return concat_limit(obj.ausgabenum_set.all())
    num_string.short_description = 'Nummer'

    def lnum_string(self, obj):
        return concat_limit(obj.ausgabelnum_set.all())
    lnum_string.short_description = 'lfd. Nummer'

    def monat_string(self, obj):
        if obj.ausgabemonat_set.exists():
            return concat_limit(
                obj.ausgabemonat_set.values_list('monat__abk', flat=True)
            )
    monat_string.short_description = 'Monate'


@admin.register(_models.Autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = _models.Autor.magazin.through
        extra = 1

    form = AutorForm
    index_category = 'Stammdaten'
    inlines = [MagazinInLine]
    list_display = ['__str__', 'person', 'kuerzel', 'magazin_string']
    list_prefetch_related = ['magazin', 'person']
    search_form_kwargs = {'fields': ['magazin', 'person', 'id__in']}

    def magazin_string(self, obj):
        return concat_limit(obj.magazin.all())
    magazin_string.short_description = 'Magazin(e)'


@admin.register(_models.artikel, site=miz_site)
class ArtikelAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.artikel.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.artikel.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.artikel.person.through
        verbose_model = _models.Person
    class AutorInLine(BaseTabularInline):
        model = _models.artikel.autor.through
        verbose_model = _models.Autor
    class MusikerInLine(BaseTabularInline):
        model = _models.artikel.musiker.through
        verbose_model = _models.Musiker
    class BandInLine(BaseTabularInline):
        model = _models.artikel.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.artikel.ort.through
        verbose_model = _models.ort
    class SpielortInLine(BaseTabularInline):
        model = _models.artikel.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.artikel.veranstaltung.through
        verbose_model = _models.veranstaltung

    form = ArtikelForm
    index_category = 'Archivgut'
    list_display_links = ['__str__', 'seite']
    save_on_top = True

    fields = [
        ('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'),
        'zusammenfassung', 'beschreibung', 'bemerkungen'
    ]
    inlines = [
        AutorInLine, GenreInLine, SchlInLine, MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine
    ]
    list_display = [
        '__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string',
        'ausgabe', 'artikel_magazin', 'kuenstler_string'
    ]
    list_prefetch_related = ['schlagwort', 'musiker', 'band']
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'schlagwort', 'genre', 'band',
            'musiker', 'autor', 'person',
            'ort', 'spielort', 'veranstaltung',
            'seite__range', 'id__in'
        ],
        'forwards': {'ausgabe': 'ausgabe__magazin'}
    }

    def zusammenfassung_string(self, obj):
        if not obj.zusammenfassung:
            return ''
        return concat_limit(obj.zusammenfassung.split(), sep=" ")
    zusammenfassung_string.short_description = 'Zusammenfassung'

    def artikel_magazin(self, obj):
        return obj.ausgabe.magazin
    artikel_magazin.short_description = 'Magazin'
    artikel_magazin.admin_order_field = 'ausgabe__magazin'

    def schlagwort_string(self, obj):
        return concat_limit(obj.schlagwort.all())
    schlagwort_string.short_description = 'Schlagwörter'

    def kuenstler_string(self, obj):
        return concat_limit(list(obj.band.all()) + list(obj.musiker.all()))
    kuenstler_string.short_description = 'Künstler'


@admin.register(_models.Band, site=miz_site)
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.Band.genre.through
    class MusikerInLine(BaseTabularInline):
        model = _models.Band.musiker.through
    class AliasInLine(BaseAliasInline):
        model = _models.BandAlias
    class OrtInLine(BaseOrtInLine):
        model = _models.Band.orte.through

    form = BandForm
    index_category = 'Stammdaten'
    inlines = [GenreInLine, AliasInLine, MusikerInLine, OrtInLine]
    list_display = ['band_name', 'genre_string', 'musiker_string', 'orte_string']
    list_prefetch_related = ['genre', 'musiker', 'bandalias_set', 'orte']
    save_on_top = True

    search_form_kwargs = {
        'fields': ['musiker', 'genre', 'orte__land', 'orte', 'id__in'],
        'labels': {'musiker': 'Mitglied'}
    }

    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'

    def musiker_string(self, obj):
        return concat_limit(obj.musiker.all())
    musiker_string.short_description = 'Mitglieder'

    def alias_string(self, obj):
        return concat_limit(obj.bandalias_set.all())
    alias_string.short_description = 'Aliase'

    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'


@admin.register(_models.bildmaterial, site=miz_site)
class BildmaterialAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.bildmaterial.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.bildmaterial.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.bildmaterial.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseTabularInline):
        model = _models.bildmaterial.musiker.through
        verbose_model = _models.Musiker
    class BandInLine(BaseTabularInline):
        model = _models.bildmaterial.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.bildmaterial.ort.through
        verbose_model = _models.ort
    class SpielortInLine(BaseTabularInline):
        model = _models.bildmaterial.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.bildmaterial.veranstaltung.through
        verbose_model = _models.veranstaltung

    collapse_all = True
    form = BildmaterialForm
    index_category = 'Archivgut'
    list_display = ['titel', 'signatur', 'size', 'datum_localized', 'veranstaltung_string']
    list_prefetch_related = ['veranstaltung']
    save_on_top = True

    inlines = [
        GenreInLine, SchlInLine, MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        PersonInLine, BestandInLine
    ]
    search_form_kwargs = {
        'fields': [
            'datum__range', 'schlagwort', 'genre', 'band','musiker', 'person',
            'ort', 'spielort', 'veranstaltung', 'reihe', 'signatur', 'id__in'
        ],
        'labels': {'reihe': 'Bildreihe'}
    }

    def datum_localized(self, obj):
        return obj.datum.localize()
    datum_localized.short_description = 'Datum'
    datum_localized.admin_order_field = 'datum'

    def veranstaltung_string(self, obj):
        return concat_limit(list(obj.veranstaltung.all()))
    veranstaltung_string.short_description = 'Veranstaltungen'

    def copy_related(self, obj):
        copy_related_set(obj, 'veranstaltung__band', 'veranstaltung__musiker')

    def response_add(self, request, obj, post_url_continue=None):
        if 'copy_related' in request.POST:
            self.copy_related(obj)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if 'copy_related' in request.POST:
            self.copy_related(obj)
        return super().response_change(request, obj)


@admin.register(_models.buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.buch.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.buch.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.buch.person.through
        verbose_model = _models.Person
    class AutorInLine(BaseTabularInline):
        model = _models.buch.autor.through
        verbose_model = _models.Autor
    class MusikerInLine(BaseTabularInline):
        model = _models.buch.musiker.through
        verbose_model = _models.Musiker
    class BandInLine(BaseTabularInline):
        model = _models.buch.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.buch.ort.through
        verbose_model = _models.ort
    class SpielortInLine(BaseTabularInline):
        model = _models.buch.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.buch.veranstaltung.through
        verbose_model = _models.veranstaltung
    class HerausgeberInLine(BaseTabularInline):
        model = _models.buch.herausgeber.through
        verbose_model = _models.Herausgeber
    class VerlagInLine(BaseTabularInline):
        model = _models.buch.verlag.through
        verbose_model = _models.verlag

    collapse_all = True
    # TODO: Semantik: Einzelbänder/Aufsätze: Teile eines Buchbandes
    crosslink_labels = {'buch': 'Aufsätze'}
    form = BuchForm
    index_category = 'Archivgut'
    save_on_top = True

    fieldsets = [
        (None, {
            'fields': [
                'titel', 'seitenumfang', 'jahr', 'auflage', 'schriftenreihe',
                ('buchband', 'is_buchband'), 'ISBN', 'EAN', 'sprache',
                'beschreibung', 'bemerkungen'
            ]}
        ),
        ('Original Angaben (bei Übersetzung)', {
            'fields': ['titel_orig', 'jahr_orig'],
            'description': "Angaben zum Original eines übersetzten Buches.",
            'classes': ['collapse', 'collapsed'],
        }),
    ]
    inlines = [
        AutorInLine, GenreInLine, SchlInLine, MusikerInLine, BandInLine,
        OrtInLine, SpielortInLine, VeranstaltungInLine,
        HerausgeberInLine, VerlagInLine, PersonInLine, BestandInLine
    ]
    list_display = [
        'titel', 'autoren_string', 'herausgeber_string', 'verlag_string',
        'schlagwort_string', 'genre_string'
    ]
    list_prefetch_related = ['autor', 'herausgeber', 'verlag', 'schlagwort', 'genre']
    search_form_kwargs = {
        'fields': [
            'autor', 'herausgeber', 'schlagwort', 'genre', 'musiker', 'band', 'person',
            'schriftenreihe', 'buchband', 'verlag', 'ort', 'spielort', 'veranstaltung',
            'jahr', 'ISBN', 'EAN', 'id__in'
        ],
        'labels': {'buchband': 'aus Buchband', 'jahr': 'Jahr'},
        # 'autor' help_text refers to quick item creation which is not allowed in search forms.
        'help_texts': {'autor': None}
    }

    def autoren_string(self, obj):
        return concat_limit(obj.autor.all())
    autoren_string.short_description = 'Autoren'

    def herausgeber_string(self, obj):
        return concat_limit(obj.herausgeber.all())
    herausgeber_string.short_description = 'Herausgeber'

    def verlag_string(self, obj):
        return concat_limit(obj.verlag.all())
    verlag_string.short_description = 'Verlag'

    def schlagwort_string(self, obj):
        return concat_limit(obj.schlagwort.all())
    schlagwort_string.short_description = 'Schlagwörter'

    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'


@admin.register(_models.dokument, site=miz_site)
class DokumentAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True


@admin.register(_models.Genre, site=miz_site)
class GenreAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.GenreAlias

    index_category = 'Stammdaten'
    inlines = [AliasInLine]
    list_display = ['genre', 'alias_string']
    list_prefetch_related = ['genrealias_set']
    search_fields = ['genre', 'genrealias__alias']

    def alias_string(self, obj):
        return concat_limit(obj.genrealias_set.all())
    alias_string.short_description = 'Aliase'


@admin.register(_models.magazin, site=miz_site)
class MagazinAdmin(MIZModelAdmin):
    class URLInLine(BaseTabularInline):
        model = _models.MagazinURL
    class VerlagInLine(BaseTabularInline):
        model = _m2m.m2m_magazin_verlag
        verbose_model = _models.verlag
    class HerausgeberInLine(BaseTabularInline):
        model = _m2m.m2m_magazin_herausgeber
        verbose_model = _models.Herausgeber
    class GenreInLine(BaseGenreInline):
        model = _models.magazin.genre.through
    class OrtInLine(BaseOrtInLine):
        model = _models.magazin.orte.through

    index_category = 'Stammdaten'
    inlines = [URLInLine, GenreInLine, VerlagInLine, HerausgeberInLine, OrtInLine]
    list_display = ['__str__', 'short_beschreibung', 'orte_string', 'anz_ausgaben']
    list_prefetch_related = ['orte']

    search_form_kwargs = {
        'fields': ['verlag', 'herausgeber', 'orte', 'genre', 'issn', 'fanzine', 'id__in'],
    }

    def anz_ausgaben(self, obj):
        return obj.anz_ausgabe
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    anz_ausgaben.admin_order_field = 'anz_ausgabe'
    anz_ausgaben.annotation = Count('ausgabe')

    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'

    def short_beschreibung(self, obj):
        return concat_limit(obj.beschreibung.split(), width=150, sep=" ")
    short_beschreibung.short_description = 'Beschreibung'

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


@admin.register(_models.memorabilien, site=miz_site)
class MemoAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True


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

    form = MusikerForm
    fields = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    index_category = 'Stammdaten'
    inlines = [GenreInLine, AliasInLine, BandInLine, OrtInLine, InstrInLine]
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'orte_string']
    list_prefetch_related = ['band_set', 'genre', 'orte']
    save_on_top = True
    search_form_kwargs = {'fields': ['person', 'genre', 'instrument', 'orte__land', 'orte', 'id__in']}

    def band_string(self, obj):
        return concat_limit(obj.band_set.all())
    band_string.short_description = 'Bands'

    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'

    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'


@admin.register(_models.Person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = _models.Person.orte.through

    fields = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    index_category = 'Stammdaten'
    inlines = [OrtInLine]
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links = ['vorname', 'nachname']
    list_prefetch_related = ['musiker_set', 'autor_set', 'orte']

    search_form_kwargs = {
        'fields': ['orte', 'orte__land', 'orte__bland', 'id__in'],
        'forwards': {'orte__bland': 'orte__land'}
    }

    def Ist_Musiker(self, obj):
        return obj.musiker_set.exists()
    Ist_Musiker.boolean = True

    def Ist_Autor(self, obj):
        return obj.autor_set.exists()
    Ist_Autor.boolean = True

    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'


@admin.register(_models.schlagwort, site=miz_site)
class SchlagwortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.schlagwort_alias
        extra = 1

    index_category = 'Stammdaten'
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string']
    list_prefetch_related = ['schlagwort_alias_set']
    search_fields = ['schlagwort', 'schlagwort_alias__alias']

    def alias_string(self, obj):
        return concat_limit(obj.schlagwort_alias_set.all())
    alias_string.short_description = 'Aliase'


@admin.register(_models.spielort, site=miz_site)
class SpielortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.spielort_alias

    list_display = ['name', 'ort']
    inlines = [AliasInLine]


@admin.register(_models.technik, site=miz_site)
class TechnikAdmin(MIZModelAdmin):
    index_category = 'Archivgut'
    inlines = [BestandInLine]
    superuser_only = True


@admin.register(_models.veranstaltung, site=miz_site)
class VeranstaltungAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.veranstaltung.genre.through
    class BandInLine(BaseTabularInline):
        model = _models.veranstaltung.band.through
        verbose_model = _models.Band
    class PersonInLine(BaseTabularInline):
        model = _models.veranstaltung.person.through
        verbose_model = _models.Person
    class SchlInLine(BaseSchlagwortInline):
        model = _models.veranstaltung.schlagwort.through
    class MusikerInLine(BaseTabularInline):
        model = _models.veranstaltung.musiker.through
        verbose_model = _models.Musiker
    class AliasInLine(BaseAliasInline):
        model = _models.veranstaltung_alias

    collapse_all = True
    inlines = [GenreInLine, SchlInLine, AliasInLine, BandInLine, MusikerInLine, PersonInLine]
    list_display = ['name', 'datum', 'spielort', 'kuenstler_string']
    list_prefetch_related = ['band', 'musiker']
    save_on_top = True

    def kuenstler_string(self, obj):
        return concat_limit(list(obj.band.all()) + list(obj.musiker.all()))
    kuenstler_string.short_description = 'Künstler'


@admin.register(_models.verlag, site=miz_site)
class VerlagAdmin(MIZModelAdmin):
    list_display = ['verlag_name', 'sitz']
    search_form_kwargs = {
        'fields': ['sitz', 'sitz__land', 'sitz__bland', 'id__in'],
        'labels': {'sitz': 'Sitz'}
    }


@admin.register(_models.video, site=miz_site)
class VideoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.video.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.video.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.video.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.video.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.video.band.through
        verbose_model = _models.Band
    class SpielortInLine(BaseTabularInline):
        model = _models.video.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.video.veranstaltung.through
        verbose_model = _models.veranstaltung

    index_category = 'Archivgut'
    superuser_only = True

    inlines = [
        GenreInLine, SchlInLine, MusikerInLine, BandInLine,
        SpielortInLine, VeranstaltungInLine, PersonInLine, BestandInLine
    ]


@admin.register(_models.bundesland, site=miz_site)
class BlandAdmin(MIZModelAdmin):
    list_display = ['bland_name', 'code', 'land']
    search_form_kwargs = {
        'fields': ['land', 'id__in'],
    }


@admin.register(_models.land, site=miz_site)
class LandAdmin(MIZModelAdmin):
    pass


@admin.register(_models.ort, site=miz_site)
class OrtAdmin(MIZModelAdmin):
    fields = ['stadt', 'land', 'bland']  # put land before bland
    index_category = 'Stammdaten'
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    search_form_kwargs = {'fields': ['land', 'bland', 'id__in']}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field == self.opts.get_field('bland'):
            kwargs['widget'] = make_widget(model=db_field.related_model, forward=['land'])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(_models.bestand, site=miz_site)
class BestandAdmin(MIZModelAdmin):
#    readonly_fields = [
#        'audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch',
#        'dokument', 'memorabilien', 'technik', 'video'
#    ]
    list_display = ['signatur', 'bestand_art', 'lagerort', 'provenienz']
    search_form_kwargs = {'fields': ['bestand_art', 'lagerort']}
    superuser_only = True

    def _check_search_form_fields(self, **kwargs):
        # Ignore the search form fields check for BestandAdmin.
        return []


@admin.register(_models.datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.datei.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.datei.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.datei.person.through
        verbose_model = _models.Person
    class MusikerInLine(BaseStackedInline):
        model = _models.datei.musiker.through
        extra = 0
        filter_horizontal = ['instrument']
        verbose_model = _models.Musiker
        fieldsets = [
            (None, {'fields': ['musiker']}),
            ("Instrumente", {'fields': ['instrument'], 'classes': ['collapse', 'collapsed']}),
        ]
    class BandInLine(BaseTabularInline):
        model = _models.datei.band.through
        verbose_model = _models.Band
    class OrtInLine(BaseTabularInline):
        model = _models.datei.ort.through
        verbose_model = _models.ort
    class SpielortInLine(BaseTabularInline):
        model = _models.datei.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.datei.veranstaltung.through
        verbose_model = _models.veranstaltung
    class QuelleInLine(BaseStackedInline):
        model = _m2m.m2m_datei_quelle
        extra = 0
        description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'

    collapse_all = True
    index_category = 'Archivgut'
    save_on_top = True
    superuser_only = True

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


@admin.register(_models.instrument, site=miz_site)
class InstrumentAdmin(MIZModelAdmin):
    list_display = ['instrument', 'kuerzel']


@admin.register(_models.Herausgeber, site=miz_site)
class HerausgeberAdmin(MIZModelAdmin):
    index_category = 'Stammdaten'


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
    list_prefetch_related = ['jahre']
    search_form_kwargs = {
        'fields': ['ausgabe__magazin', 'ausgabe', 'genre', 'jahre__jahr', 'id__in']}

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
            })
            fieldsets.insert(1, fieldset)
            default_fieldset['fields'] = fields
        return fieldsets

    def jahr_string(self, obj):
        return concat_limit(obj.jahre.all())
    jahr_string.short_description = 'Jahre'
    jahr_string.admin_order_field = 'jahr'
    jahr_string.annotation = Min('jahre__jahr')


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
            'jahre__jahr', 'id__in'
        ]
    }


@admin.register(_models.Katalog, site=miz_site)
class KatalogAdmin(BaseBrochureAdmin):

    list_display = ['titel', 'zusammenfassung', 'art', 'jahr_string']

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


@admin.register(_models.Kalendar, site=miz_site)
class KalendarAdmin(BaseBrochureAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.BaseBrochure.genre.through
    class JahrInLine(BaseTabularInline):
        model = _models.BrochureYear
    class SpielortInLine(BaseTabularInline):
        model = _models.Kalendar.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.Kalendar.veranstaltung.through
        verbose_model = _models.veranstaltung
    class URLInLine(BaseTabularInline):
        model = _models.BrochureURL

    inlines = [
        URLInLine, JahrInLine, GenreInLine, SpielortInLine,
        VeranstaltungInLine, BestandInLine]
    search_form_kwargs = {
        'fields': [
            'ausgabe__magazin', 'ausgabe', 'genre', 'spielort', 'veranstaltung',
            'jahre__jahr', 'id__in'
        ]
    }


@admin.register(
    _models.monat, _models.lagerort, _models.geber, _models.plattenfirma,
    _models.provenienz, _models.Format, _models.FormatTag, _models.FormatSize,
    _models.FormatTyp, _models.schriftenreihe, _models.Bildreihe, _models.Veranstaltungsreihe,
    site=miz_site
)
class HiddenFromIndex(MIZModelAdmin):
    superuser_only = True


miz_site.register(Group, GroupAdmin)
miz_site.register(User, UserAdmin)
