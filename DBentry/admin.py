from django.contrib import admin
from django.db.models import Count, Min

import DBentry.models as _models
import DBentry.m2m as _m2m
import DBentry.actions as _actions
from DBentry.base.admin import (
    MIZModelAdmin, BaseAliasInline, BaseAusgabeInline, BaseGenreInline, BaseSchlagwortInline, 
    BaseStackedInline, BaseTabularInline, BaseOrtInLine
)
from DBentry.forms import ArtikelForm, AutorForm, BuchForm, HerausgeberForm, BrochureForm, AudioForm
from DBentry.utils import concat_limit
from DBentry.ac.widgets import make_widget
from DBentry.constants import ZRAUM_ID, DUPLETTEN_ID

from DBentry.sites import miz_site

class BestandInLine(BaseTabularInline):
    model = _models.bestand
    readonly_fields = ['signatur']
    classes = ['copylast']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = _models.bestand._meta.verbose_name
    verbose_name_plural = _models.bestand._meta.verbose_name_plural
    
class DateiInLine(BaseTabularInline):
    model = _m2m.m2m_datei_quelle
    verbose_model = _models.datei
    fields = ['datei']

class QuelleInLine(BaseStackedInline):
    extra = 0
    model = _m2m.m2m_datei_quelle
    description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'
        
        
@admin.register(_models.audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.audio.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.audio.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.audio.person.through
        verbose_model = _models.person
    class MusikerInLine(BaseStackedInline):
        model = _models.audio.musiker.through
        verbose_model = _models.musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(BaseTabularInline):
        model = _models.audio.band.through
        verbose_model = _models.band
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
            (None, {'fields' : ['anzahl', 'format_typ', 'format_size', 'catalog_nr', 'tape', 'channel', 'noise_red']}), 
            ('Tags', {'fields' : ['tag'], 'classes' : ['collapse', 'collapsed']}), 
            ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class OrtInLine(BaseTabularInline):
        model = _models.audio.ort.through
        verbose_model = _models.ort
    class PlattenInLine(BaseTabularInline):
        model = _models.audio.plattenfirma.through
        verbose_model = _models.plattenfirma
    class AusgabeInLine(BaseAusgabeInline):
        model = _models.ausgabe.audio.through
        
    form = AudioForm
    index_category = 'Archivgut'
    
    list_display = ['__str__', 'formate_string', 'kuenstler_string']
    
    inlines = [PlattenInLine, FormatInLine, DateiInLine, MusikerInLine, BandInLine, GenreInLine, SchlInLine, 
            VeranstaltungInLine, SpielortInLine, OrtInLine, PersonInLine, BestandInLine, AusgabeInLine]
    fieldsets = [
        (None, {'fields' : ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'sender']}), 
        ('Discogs', {'fields' : ['release_id', 'discogs_url'], 'classes' : ['collapse', 'collapsed']}), 
        ('Beschreibung & Bemerkungen', {'fields' : ['beschreibung', 'bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
    ]
    save_on_top = True
    collapse_all = True
    
    advanced_search_form = {
        'selects' : ['musiker', 'band', 'genre', 'spielort', 'veranstaltung', 'plattenfirma', 
                        'format__format_size', 'format__format_typ', 'format__tag'], 
        'simple' : ['release_id'], 
        'labels' : {'format__tag':'Tags'}, 
    }
        
    def kuenstler_string(self, obj):
        return concat_limit(list(obj.band.all()) + list(obj.musiker.all()))
    kuenstler_string.short_description = 'Künstler'
    
    def formate_string(self, obj):
        return concat_limit(list(obj.format_set.all()))
    formate_string.short_description = 'Format'
    

@admin.register(_models.ausgabe, site=miz_site)
class AusgabenAdmin(MIZModelAdmin):
    class NumInLine(BaseTabularInline):
        model = _models.ausgabe_num
        extra = 0
    class MonatInLine(BaseTabularInline):
        model = _models.ausgabe_monat
        verbose_model = _models.monat
        extra = 0
    class LNumInLine(BaseTabularInline):
        model = _models.ausgabe_lnum
        extra = 0
    class JahrInLine(BaseTabularInline):
        model = _models.ausgabe_jahr
        extra = 0
        verbose_name_plural = 'erschienen im Jahr'
    class AudioInLine(BaseTabularInline):
        model = _models.ausgabe.audio.through
        
    index_category = 'Archivgut'
    
    actions = MIZModelAdmin.actions + [_actions.bulk_jg, _actions.add_bestand, _actions.moveto_brochure]
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahr_string', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
    
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine, AudioInLine]
    fields = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
    flds_to_group = [('status', 'sonderausgabe')]
    
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat__ordinal'], 
        'selects':['magazin','status'], 
        'simple':['jahrgang', 'sonderausgabe'], 
        'labels' : {'ausgabe_monat__monat__ordinal':'Monatsnummer'}
    }
    
    def get_changelist(self, request, **kwargs):
        from .changelist import AusgabeChangeList
        return AusgabeChangeList
    
    def anz_artikel(self, obj):
        return obj.artikel_set.count()
    anz_artikel.short_description = 'Anz. Artikel'
    anz_artikel.admin_order_field = ('anz', Count, 'artikel', {'distinct': True})
    
    def jahr_string(self, obj):
        return concat_limit(obj.ausgabe_jahr_set.all())
    jahr_string.short_description = 'Jahre'
    
    def num_string(self, obj):
        return concat_limit(obj.ausgabe_num_set.all())
    num_string.short_description = 'Nummer'
    
    def lnum_string(self, obj):
        return concat_limit(obj.ausgabe_lnum_set.all())
    lnum_string.short_description = 'lfd. Nummer'
    
    def monat_string(self, obj):
        if obj.ausgabe_monat_set.exists():
            return concat_limit(obj.ausgabe_monat_set.values_list('monat__abk', flat=True))
    monat_string.short_description = 'Monate'
    
    #TODO: replace zbestand/dbestand with just a count of bestand (zbestand should be 1 at all times anyway)
    def zbestand(self, obj):
        return obj.bestand_set.filter(lagerort=_models.lagerort.objects.filter(pk=ZRAUM_ID).first()).exists()
    zbestand.short_description = 'Bestand: ZRaum'
    zbestand.boolean = True
    
    def dbestand(self, obj):
        return obj.bestand_set.filter(lagerort=_models.lagerort.objects.filter(pk=DUPLETTEN_ID).first()).exists()
    dbestand.short_description = 'Bestand: Dublette'
    dbestand.boolean = True
    
    
@admin.register(_models.autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = _models.autor.magazin.through
        extra = 1
    
    form = AutorForm
    index_category = 'Stammdaten'
    
    list_display = ['__str__', 'person','kuerzel','magazin_string']
    
    inlines = [MagazinInLine]

    advanced_search_form = {
        'selects' : ['magazin']
    }
            
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
        verbose_model = _models.person
    class AutorInLine(BaseTabularInline):
        model = _models.artikel.autor.through
        verbose_model = _models.autor        
    class MusikerInLine(BaseTabularInline):
        model = _models.artikel.musiker.through
        verbose_model = _models.musiker
    class BandInLine(BaseTabularInline):
        model = _models.artikel.band.through
        verbose_model = _models.band
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
    
    list_display = ['__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string','ausgabe','artikel_magazin', 'kuenstler_string']
    list_display_links = ['__str__', 'seite']
    
    inlines = [AutorInLine, SchlInLine, MusikerInLine, BandInLine, GenreInLine, OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine]
    fields = [('ausgabe__magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'beschreibung', 'bemerkungen']
    save_on_top = True
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', ('ausgabe', 'ausgabe__magazin'), 'schlagwort', 'genre', 'band', 'musiker', 'autor'], 
        'simple':[], 
    }  

    def get_queryset(self, request):
        #TODO: rethink this now that we have chronologic_order for ausgabe -- also monat_id should not longer used
        #NOTE: what actually uses ModelAdmin.get_queryset? Because the changelist's results are 
        # ordered via chronologic_order.
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite', 'pk')
        return qs
    
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
        
@admin.register(_models.band, site=miz_site)    
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.band.genre.through
    class MusikerInLine(BaseTabularInline):
        model = _models.band.musiker.through
    class AliasInLine(BaseAliasInline):
        model = _models.band_alias
    class OrtInLine(BaseOrtInLine):
        model = _models.band.orte.through
        
    index_category = 'Stammdaten'
    
    list_display = ['band_name', 'genre_string', 'musiker_string', 'orte_string']

    inlines=[GenreInLine, OrtInLine, AliasInLine, MusikerInLine]
    googlebtns = ['band_name']
    save_on_top = True
    
    advanced_search_form = {
        'selects' : ['musiker', 'genre', 'orte__land', 'orte'], 
        'labels' : {'musiker':'Mitglied'}
    }
        
    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'
        
    def musiker_string(self, obj):
        return concat_limit(obj.musiker.all())
    musiker_string.short_description = 'Mitglieder'
    
    def alias_string(self, obj):
        return concat_limit(obj.band_alias_set.all())
    alias_string.short_description = 'Aliase'
    
    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'
    
@admin.register(_models.bildmaterial, site=miz_site)
class BildmaterialAdmin(MIZModelAdmin):
    superuser_only = True
    index_category = 'Archivgut'
    
@admin.register(_models.buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.buch.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.buch.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.buch.person.through
        verbose_model = _models.person
    class AutorInLine(BaseTabularInline):
        model = _models.buch.autor.through
        verbose_model = _models.autor
    class MusikerInLine(BaseTabularInline):
        model = _models.buch.musiker.through
        verbose_model = _models.musiker
    class BandInLine(BaseTabularInline):
        model = _models.buch.band.through
        verbose_model = _models.band
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
    form = BuchForm
    index_category = 'Archivgut'
    
    list_display = ['titel', 'auflage', 'schriftenreihe', 'verlag', 'autoren_string', 'herausgeber_string', 'schlagwort_string', 'genre_string']
    
    inlines = [
        HerausgeberInLine, AutorInLine, SchlInLine, MusikerInLine, BandInLine, GenreInLine, OrtInLine, 
        SpielortInLine, VeranstaltungInLine, PersonInLine, BestandInLine
    ]
    collapse_all = True
    save_on_top = True
    
    fieldsets = [
        (None, {'fields': [
            'titel', 'seitenumfang', 'jahr', 'auflage', 'schriftenreihe', ('buchband', 'is_buchband'), 'verlag', 
            'ISBN', 'EAN', 'sprache', 
            ]
        }), 
        ('Original Angaben (bei Übersetzung)', {
            'fields':['titel_orig', 'jahr_orig'], 
            'description' : "Angaben zum Original eines übersetzten Buches.", 
            'classes':['collapse','collapsed'], 
            }
        ),
        ('Beschreibung & Bemerkungen', {'fields' : ['beschreibung', 'bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
    ]
    
    advanced_search_form = {
        'selects' : [
            'autor', 'herausgeber', 'schlagwort', 'genre', 'musiker', 'band', 'person', 
            'schriftenreihe', 'buchband', 'verlag', 'sprache', 
        ], 
        'simple' : ['jahr', 'ISBN', 'EAN'], 
        'labels' : {'buchband': 'aus Buchband', 'jahr':'Jahr'}, 
    }
    
    crosslink_labels = {
        'buch' : 'Aufsätze', #TODO: Semantik: Einzelbänder/Aufsätze: Teile eines Buchbandes
    }
    
    def autoren_string(self, obj):
        return concat_limit(obj.autor.all())
    autoren_string.short_description = 'Autoren'
    
    def herausgeber_string(self, obj):
        return concat_limit(obj.herausgeber.all())
    herausgeber_string.short_description = 'Herausgeber'
    
    def schlagwort_string(self, obj):
        return concat_limit(obj.schlagwort.all())
    schlagwort_string.short_description = 'Schlagwörter'
    
    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'
    
@admin.register(_models.dokument, site=miz_site)
class DokumentAdmin(MIZModelAdmin):
    
    superuser_only = True
    index_category = 'Archivgut'
    
    inlines = [BestandInLine]
    
@admin.register(_models.genre, site=miz_site)
class GenreAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.genre_alias
    
    index_category = 'Stammdaten'
        
    list_display = ['genre', 'alias_string', 'ober_string', 'sub_string']
    search_fields = ['genre', 'sub_genres__genre', 'genre_alias__alias'] # Removed the 'ober' field from search_fields (useful for dal searches, not so much on changelists)
    
    inlines = [AliasInLine]
        
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Obergenre'
    ober_string.admin_order_field = 'ober'
    
    def sub_string(self, obj):
        return concat_limit(obj.sub_genres.all())
    sub_string.short_description = 'Subgenres'
        
    def alias_string(self, obj):
        return concat_limit(obj.genre_alias_set.all())
    alias_string.short_description = 'Aliase'

@admin.register(_models.magazin, site=miz_site)
class MagazinAdmin(MIZModelAdmin):
    class VerlagInLine(BaseTabularInline):
        model = _m2m.m2m_magazin_verlag
        verbose_model = _models.verlag
    class HerausgeberInLine(BaseTabularInline):
        model = _m2m.m2m_magazin_herausgeber
        verbose_model = _models.Herausgeber
    class GenreInLine(BaseGenreInline):
        model = _models.magazin.genre.through
        
    index_category = 'Stammdaten'
        
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    
    inlines = [VerlagInLine, HerausgeberInLine, GenreInLine]
    
    advanced_search_form = {
        'simple': ['issn', 'fanzine'], 
        'selects': ['m2m_magazin_verlag', 'm2m_magazin_herausgeber', 'ort', 'genre'], 
        'labels': {'m2m_magazin_verlag':'Verlag', 'm2m_magazin_herausgeber': 'Herausgeber', 'ort': 'Herausgabeort'}, 
    }
        
    def anz_ausgaben(self, obj):
        return obj.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    anz_ausgaben.admin_order_field = ('anz', Count, 'ausgabe', {})

@admin.register(_models.memorabilien, site=miz_site)
class MemoAdmin(MIZModelAdmin):
    
    superuser_only = True
    index_category = 'Archivgut'
    
    inlines = [BestandInLine]

@admin.register(_models.musiker, site=miz_site)
class MusikerAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.musiker.genre.through
    class BandInLine(BaseTabularInline):
        model = _models.band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
    class AliasInLine(BaseAliasInline):
        model = _models.musiker_alias
    class InstrInLine(BaseTabularInline):
        model = _models.musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    class OrtInLine(BaseOrtInLine):
        model = _models.musiker.orte.through
        
    index_category = 'Stammdaten'
        
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'orte_string']
    
    inlines = [GenreInLine, OrtInLine, AliasInLine, BandInLine, InstrInLine]
    fields = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    googlebtns = ['kuenstler_name']
    save_on_top = True
    
    advanced_search_form = {
        'selects' : ['person', 'genre', 'band', 
                'instrument','orte__land', 'orte'], 
    }
        
    def band_string(self, obj):
        return concat_limit(obj.band_set.all())
    band_string.short_description = 'Bands'
    
    def genre_string(self, obj):
        return concat_limit(obj.genre.all())
    genre_string.short_description = 'Genres'
    
    def orte_string(self, obj):
        return concat_limit(obj.orte.all())
    orte_string.short_description = 'Orte'
    
@admin.register(_models.person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = _models.person.orte.through
    inlines = [OrtInLine]
    
    index_category = 'Stammdaten'
    
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    
    fields = ['vorname', 'nachname', 'beschreibung', 'bemerkungen']
    
    advanced_search_form = {
        'selects' : ['orte', 'orte__land', ('orte__bland', 'orte__land')]
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
        
    list_display = ['schlagwort', 'alias_string', 'ober_string', 'sub_string']
    search_fields = ['schlagwort', 'unterbegriffe__schlagwort', 'schlagwort_alias__alias'] # Removed the 'ober' field from search_fields (useful for dal searches, not so much on changelists)
    
    inlines = [AliasInLine]
    
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Oberbegriff'
    ober_string.admin_order_field = 'ober'
    
    def sub_string(self, obj):
        return concat_limit(obj.unterbegriffe.all())
    sub_string.short_description = 'Unterbegriffe'
        
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
    
    superuser_only = True
    index_category = 'Archivgut'
    
    inlines = [BestandInLine]

@admin.register(_models.veranstaltung, site=miz_site)
class VeranstaltungAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.veranstaltung.genre.through
    class BandInLine(BaseTabularInline):
        model = _models.veranstaltung.band.through
        verbose_model = _models.band
    class PersonInLine(BaseTabularInline):
        model = _models.veranstaltung.person.through
        verbose_model = _models.person
    class SchlInLine(BaseSchlagwortInline):
        model = _models.veranstaltung.schlagwort.through
    class MusikerInLine(BaseTabularInline):
        model = _models.veranstaltung.musiker.through
        verbose_model = _models.musiker
    class AliasInLine(BaseAliasInline):
        model = _models.veranstaltung_alias
    inlines=[GenreInLine, PersonInLine, BandInLine, MusikerInLine, SchlInLine, AliasInLine]
    
@admin.register(_models.verlag, site=miz_site)
class VerlagAdmin(MIZModelAdmin):
    list_display = ['verlag_name', 'sitz']
    advanced_search_form = {
        'selects' : ['sitz','sitz__land', 'sitz__bland'], 
        'labels' : {'sitz':'Sitz'}
    }
    
        
@admin.register(_models.video, site=miz_site)
class VideoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.video.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.video.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.video.person.through
        verbose_model = _models.person
    class MusikerInLine(BaseStackedInline):
        model = _models.video.musiker.through
        verbose_model = _models.musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(BaseTabularInline):
        model = _models.video.band.through
        verbose_model = _models.band
    class SpielortInLine(BaseTabularInline):
        model = _models.video.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.video.veranstaltung.through
        verbose_model = _models.veranstaltung
    
    superuser_only = True
    index_category = 'Archivgut'
        
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]
        
@admin.register(_models.bundesland, site=miz_site)
class BlandAdmin(MIZModelAdmin):
    list_display = ['bland_name', 'code', 'land']
    advanced_search_form = {
        'selects' : ['ort__land'], 
    }
    
@admin.register(_models.land, site=miz_site)
class LandAdmin(MIZModelAdmin):
    pass
    
@admin.register(_models.kreis, site=miz_site)
class KreisAdmin(MIZModelAdmin):
    superuser_only = True
    
@admin.register(_models.ort, site=miz_site)
class OrtAdmin(MIZModelAdmin):
    
    index_category = 'Stammdaten'
    
    fields = ['stadt', 'land', 'bland'] # put land before bland
    
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    
    advanced_search_form = {
        'selects' : ['land', 'bland']
    }
            
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field == self.opts.get_field('bland'):
            kwargs['widget'] = make_widget(model=db_field.related_model, forward=['land'])
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
@admin.register(_models.bestand, site=miz_site)
class BestandAdmin(MIZModelAdmin):
    #readonly_fields = ['audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch', 'dokument', 'memorabilien', 'technik', 'video']
    list_display = ['signatur', 'bestand_art', 'lagerort','provenienz']
    #flds_to_group = [('ausgabe', 'ausgabe_magazin')]
    
    superuser_only = True
    advanced_search_form = {
        'selects' : ['bestand_art', 'lagerort'], 
    }
    
@admin.register(_models.datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = _models.datei.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = _models.datei.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = _models.datei.person.through
        verbose_model = _models.person
    class MusikerInLine(BaseStackedInline):
        model = _models.datei.musiker.through
        verbose_model = _models.musiker
        filter_horizontal = ['instrument']
        extra = 0
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(BaseTabularInline):
        model = _models.datei.band.through
        verbose_model = _models.band
    class OrtInLine(BaseTabularInline):
        model = _models.datei.ort.through
        verbose_model = _models.ort
    class SpielortInLine(BaseTabularInline):
        model = _models.datei.spielort.through
        verbose_model = _models.spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = _models.datei.veranstaltung.through
        verbose_model = _models.veranstaltung
        
    superuser_only = True
    index_category = 'Archivgut'
    
    inlines = [QuelleInLine, BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, OrtInLine]
    fieldsets = [
        (None, { 'fields': ['titel', 'media_typ', 'datei_pfad', 'provenienz']}),
        ('Allgemeine Beschreibung', { 'fields' : ['beschreibung', 'quelle', 'sender', 'bemerkungen']}),  
    ]
    save_on_top = True
    collapse_all = True
    hint = 'Diese Seite ist noch nicht vollständig fertig gestellt. Bitte noch nicht benutzen.'
    
@admin.register(_models.instrument, site=miz_site)
class InstrumentAdmin(MIZModelAdmin):
    list_display = ['instrument', 'kuerzel']
    
@admin.register(_models.Herausgeber, site=miz_site)
class HerausgeberAdmin(MIZModelAdmin):
    form = HerausgeberForm
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
    list_display = ['titel', 'zusammenfassung', 'jahr_string']
    inlines = [URLInLine, JahrInLine, GenreInLine, BestandInLine]
    advanced_search_form = {
        'selects': ['genre'], 
        'gtelt': ['jahre__jahr']
    }
    
    def get_fieldsets(self, request, obj=None):
        # Add a fieldset for (ausgabe, ausgabe__magazin)
        fieldsets = super().get_fieldsets(request, obj)
        # django default implementation adds at minimum: [(None, {'fields': self.get_fields()})]
        none_fieldsets = list(filter(lambda tpl: tpl[0] is None, fieldsets))
        if none_fieldsets:
            none_fieldset_fields = none_fieldsets[0][1]['fields']
            if 'ausgabe' in none_fieldset_fields and 'ausgabe__magazin' in none_fieldset_fields:
                none_fieldset_fields.remove('ausgabe')
                none_fieldset_fields.remove('ausgabe__magazin')
                fieldsets.insert(1, ('Beilage von Ausgabe', {
                    'fields':[('ausgabe__magazin', 'ausgabe')], 
                    'description':'Geben Sie die Ausgabe an, der dieses Objekt beilag.'
                }))
        return fieldsets
        
    def jahr_string(self, obj):
        return concat_limit(obj.jahre.all())
    jahr_string.short_description = 'Jahre'
    jahr_string.admin_order_field = {'jahr': Min('jahre__jahr')}
    
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
    
@admin.register(_models.Katalog, site=miz_site)
class KatalogAdmin(BaseBrochureAdmin):
    
    list_display = ['titel', 'zusammenfassung', 'art', 'jahr_string']

    def get_fieldsets(self, *args, **kwargs):
        # swap art and zusammenfassung without having to redeclare the entire fieldsets attribute
        fieldsets = super().get_fieldsets(*args, **kwargs)
        try:
            none_fieldset = list(filter(lambda tpl: tpl[0] is None, fieldsets))[0]
            fields = none_fieldset[1]['fields']
            art = fields.index('art')
            zusammenfassung = fields.index('zusammenfassung')
            fields[art], fields[zusammenfassung] = fields[zusammenfassung], fields[art]
        except (IndexError, KeyError):
            # Either there is no 'None' fieldset, or it does not contain any fields or 'art' and/or 'zusammenfassung' are missing from fields
            pass
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
        
    inlines = [URLInLine, JahrInLine, GenreInLine, SpielortInLine, VeranstaltungInLine, BestandInLine]
    
@admin.register(_models.sender, site = miz_site)
class SenderAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = _models.sender_alias
        
    inlines = [AliasInLine]
    
@admin.register(
    _models.monat, _models.lagerort, _models.geber, _models.sprache, _models.plattenfirma, _models.provenienz, 
    _models.Format, _models.FormatTag, _models.FormatSize, _models.FormatTyp, _models.NoiseRed, _models.Organisation, _models.schriftenreihe, 
    site=miz_site
)
class HiddenFromIndex(MIZModelAdmin):
    superuser_only = True

from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
miz_site.register(Group, GroupAdmin)
miz_site.register(User, UserAdmin)
