from django.contrib import admin

from .models import *
from .base.admin import (
    MIZModelAdmin, BaseAliasInline, BaseAusgabeInline, BaseGenreInline, BaseSchlagwortInline, 
    BaseStackedInline, BaseTabularInline, BaseOrtInLine
)
from .forms import ArtikelForm, AutorForm
from .utils import concat_limit
from .actions import *

from .sites import miz_site

class BestandInLine(BaseTabularInline):
    model = bestand
    readonly_fields = ['signatur']
    fields = ['signatur', 'lagerort', 'provenienz']
    verbose_name = bestand._meta.verbose_name
    verbose_name_plural = bestand._meta.verbose_name_plural
    
class DateiInLine(BaseTabularInline):
    model = m2m_datei_quelle
    verbose_model = datei
    fields = ['datei']

class QuelleInLine(BaseStackedInline):
    extra = 0
    model = m2m_datei_quelle
    description = 'Verweise auf das Herkunfts-Medium (Tonträger, Videoband, etc.) dieser Datei.'
        
        
@admin.register(audio, site=miz_site)
class AudioAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = audio.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = audio.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = audio.person.through
        verbose_model = person
    class MusikerInLine(BaseStackedInline):
        model = audio.musiker.through
        verbose_model = musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(BaseTabularInline):
        model = audio.band.through
        verbose_model = band
    class SpielortInLine(BaseTabularInline):
        model = audio.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = audio.veranstaltung.through
        verbose_model = veranstaltung
    class FormatInLine(BaseStackedInline):
        model = Format
        extra = 0
        filter_horizontal = ['tag']
        fieldsets = [
            (None, {'fields' : ['anzahl', 'format_typ', 'format_size', 'catalog_nr', 'tape', 'channel', 'noise_red']}), 
            ('Tags', {'fields' : ['tag'], 'classes' : ['collapse', 'collapsed']}), 
            ('Bemerkungen', {'fields' : ['bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class OrtInLine(BaseTabularInline):
        model = audio.ort.through
        verbose_model = ort
    class PlattenInLine(BaseTabularInline):
        model = audio.plattenfirma.through
        verbose_model = plattenfirma
    class AusgabeInLine(BaseAusgabeInline):
        model = ausgabe.audio.through
    index_category = 'Archivgut'
    inlines = [PlattenInLine, FormatInLine, DateiInLine, MusikerInLine, BandInLine, GenreInLine, SchlInLine, 
            VeranstaltungInLine, SpielortInLine, OrtInLine, PersonInLine, BestandInLine, AusgabeInLine]
    fieldsets = [
        (None, {'fields' : ['titel', 'tracks', 'laufzeit', 'e_jahr', 'quelle', 'sender']}), 
        ('Discogs', {'fields' : ['release_id', 'discogs_url'], 'classes' : ['collapse', 'collapsed']}), 
        ('Beschreibung & Bemerkungen', {'fields' : ['beschreibung', 'bemerkungen'], 'classes' : ['collapse', 'collapsed']}), 
    ]
    list_display = ['__str__', 'formate_string', 'kuenstler_string']
    save_on_top = True
    collapse_all = True
    
    advanced_search_form = {
        'selects' : ['musiker', 'band', 'genre', 'spielort', 'veranstaltung', 'plattenfirma', 
                        'format__format_size', 'format__format_typ', 'format__tag'], 
        'simple' : ['release_id'], 
        'labels' : {'format__tag':'Tags'}, 
    }
    

@admin.register(ausgabe, site=miz_site)
class AusgabenAdmin(MIZModelAdmin):
    class NumInLine(BaseTabularInline):
        model = ausgabe_num
        extra = 0
    class MonatInLine(BaseTabularInline):
        model = ausgabe_monat
        extra = 0
    class LNumInLine(BaseTabularInline):
        model = ausgabe_lnum
        extra = 0
    class JahrInLine(BaseTabularInline):
        model = ausgabe_jahr
        extra = 0
        verbose_name_plural = 'erschienen im Jahr'
    class AudioInLine(BaseTabularInline):
        model = ausgabe.audio.through
    inlines = [NumInLine,  MonatInLine, LNumInLine, JahrInLine,BestandInLine, AudioInLine]
    flds_to_group = [('status', 'sonderausgabe')]
    index_category = 'Archivgut'
    
    list_display = ('__str__', 'num_string', 'lnum_string','monat_string','jahr_string', 'jahrgang', 
                        'magazin','e_datum','anz_artikel', 'status') 
                            
    actions = [bulk_jg, add_bestand]
    fields = ['magazin', ('status', 'sonderausgabe'), 'e_datum', 'jahrgang', 'beschreibung', 'bemerkungen']
    advanced_search_form = {
        'gtelt':['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum'], 
        'selects':['magazin','status'], 
        'simple':['jahrgang', 'sonderausgabe']
    }
                
    def anz_artikel(self, obj):
        return obj.artikel_set.count()
    anz_artikel.short_description = 'Anz. Artikel'
    
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
    
    def zbestand(self, obj):
        return obj.bestand_set.filter(lagerort=lagerort.objects.filter(pk=ZRAUM_ID)).exists()
    zbestand.short_description = 'Bestand: ZRaum'
    zbestand.boolean = True
    
    def dbestand(self, obj):
        return obj.bestand_set.filter(lagerort=lagerort.objects.filter(pk=DUPLETTEN_ID)).exists()
    dbestand.short_description = 'Bestand: Dublette'
    dbestand.boolean = True
    
    
@admin.register(autor, site=miz_site)
class AutorAdmin(MIZModelAdmin):
    class MagazinInLine(BaseTabularInline):
        model = autor.magazin.through
        extra = 1
    
    form = AutorForm
    index_category = 'Stammdaten'
    
    inlines = [MagazinInLine]
    
    list_display = ['__str__', 'magazin_string']

    advanced_search_form = {
        'selects' : ['magazin']
    }
            
    def magazin_string(self, obj):
        return concat_limit(obj.magazin.all())
    magazin_string.short_description = 'Magazin(e)'
    
@admin.register(artikel, site=miz_site)
class ArtikelAdmin(MIZModelAdmin):  
    class GenreInLine(BaseGenreInline):
        model = artikel.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = artikel.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = artikel.person.through
        verbose_model = person
    class AutorInLine(BaseTabularInline):
        model = artikel.autor.through
        verbose_model = autor
    class MusikerInLine(BaseTabularInline):
        model = artikel.musiker.through
        verbose_model = musiker
    class BandInLine(BaseTabularInline):
        model = artikel.band.through
        verbose_model = band
    class OrtInLine(BaseTabularInline):
        model = artikel.ort.through
        verbose_model = ort
    class SpielortInLine(BaseTabularInline):
        model = artikel.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = artikel.veranstaltung.through
        verbose_model = veranstaltung
    form = ArtikelForm
    inlines = [AutorInLine, SchlInLine, MusikerInLine, BandInLine, GenreInLine, OrtInLine, SpielortInLine, VeranstaltungInLine, PersonInLine]
    flds_to_group = [('magazin', 'ausgabe'),('seite', 'seitenumfang'),]
    index_category = 'Archivgut'
    
    list_display = ['__str__', 'zusammenfassung_string', 'seite', 'schlagwort_string','ausgabe','artikel_magazin', 'kuenstler_string']
    list_display_links = ['__str__', 'seite']
    fields = [('magazin', 'ausgabe'), 'schlagzeile', ('seite', 'seitenumfang'), 'zusammenfassung', 'beschreibung', 'bemerkungen']
                                
    advanced_search_form = {
        'gtelt':['seite', ], 
        'selects':['ausgabe__magazin', ('ausgabe', 'ausgabe__magazin'), 'schlagwort', 'genre', 'band', 'musiker', 'autor'], 
        'simple':[], 
    }  
    save_on_top = True

    def get_queryset(self, request):
        # NOTE: resultbased_ordering?
        from django.db.models import Min
        qs = super(ArtikelAdmin, self).get_queryset(request)
        qs = qs.annotate(
                jahre = Min('ausgabe__ausgabe_jahr__jahr'), 
                nums = Min('ausgabe__ausgabe_num__num'), 
                lnums = Min('ausgabe__ausgabe_lnum__lnum'), 
                monate = Min('ausgabe__ausgabe_monat__monat_id'), 
                ).order_by('ausgabe__magazin__magazin_name', 'jahre', 'nums', 'lnums', 'monate', 'seite', 'pk')
        return qs
        
@admin.register(band, site=miz_site)    
class BandAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = band.genre.through
    class MusikerInLine(BaseTabularInline):
        model = band.musiker.through
    class AliasInLine(BaseAliasInline):
        model = band_alias
    class OrtInLine(BaseOrtInLine):
        model = band.orte.through
        
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
    
@admin.register(bildmaterial, site=miz_site)
class BildmaterialAdmin(MIZModelAdmin):
    superuser_only = True
    index_category = 'Archivgut'
    
@admin.register(buch, site=miz_site)
class BuchAdmin(MIZModelAdmin):
    class AutorInLine(BaseTabularInline):
        model = buch.autor.through
        verbose_model = autor
    save_on_top = True
    index_category = 'Archivgut'
    inlines = [AutorInLine, BestandInLine]
    flds_to_group = [('jahr', 'verlag'), ('jahr_orig','verlag_orig'), ('EAN', 'ISBN'), ('sprache', 'sprache_orig')]
    search_fields = ['pk','titel']
    advanced_search_form = {
        'selects' : ['verlag', 'sprache'], 
        'simple' : [], 
        'labels' : {}, 
    }
    
@admin.register(dokument, site=miz_site)
class DokumentAdmin(MIZModelAdmin):
    superuser_only = True
    index_category = 'Archivgut'
    infields = [BestandInLine]
    
@admin.register(genre, site=miz_site)
class GenreAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = genre_alias
    index_category = 'Stammdaten'
    search_fields = ['genre', 'sub_genres__genre', 'genre_alias__alias']
    inlines = [AliasInLine]
    list_display = ['genre', 'alias_string', 'ober_string']
        
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Obergenre'
        
    def alias_string(self, obj):
        return concat_limit(obj.genre_alias_set.all())
    alias_string.short_description = 'Aliase'
    

@admin.register(magazin, site=miz_site)
class MagazinAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = magazin.genre.through
        magazin.genre.through.verbose_name = ''
    inlines = [GenreInLine]
    
    index_category = 'Stammdaten'
    list_display = ('__str__','beschreibung','anz_ausgaben', 'ort')
    
    advanced_search_form = {
        'selects' : ['ort__land'], 
        'labels' : {'ort__land':'Herausgabeland'}
    }
        
    def anz_ausgaben(self, obj):
        return obj.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'

@admin.register(memorabilien, site=miz_site)
class MemoAdmin(MIZModelAdmin):
    superuser_only = True
    index_category = 'Archivgut'
    inlines = [BestandInLine]

@admin.register(musiker, site=miz_site)
class MusikerAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = musiker.genre.through
    class BandInLine(BaseTabularInline):
        model = band.musiker.through
        verbose_name_plural = 'Ist Mitglied in'
        verbose_name = 'Band'
    class AliasInLine(BaseAliasInline):
        model = musiker_alias
    class InstrInLine(BaseTabularInline):
        model = musiker.instrument.through
        verbose_name_plural = 'Spielt Instrument'
        verbose_name = 'Instrument'
    class OrtInLine(BaseOrtInLine):
        model = musiker.orte.through
        
    index_category = 'Stammdaten'
        
    list_display = ['kuenstler_name', 'genre_string', 'band_string', 'orte_string']
    
    inlines = [GenreInLine, OrtInLine, AliasInLine, BandInLine, InstrInLine]
    fields = ['kuenstler_name', 'person', 'beschreibung', 'bemerkungen']
    googlebtns = ['kuenstler_name']
    save_on_top = True
    
    advanced_search_form = {
        'selects' : ['person', 'genre', 'band', 
                'instrument','person__orte__land', 'person__orte'], 
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
    
@admin.register(person, site=miz_site)
class PersonAdmin(MIZModelAdmin):
    class OrtInLine(BaseOrtInLine):
        model = person.orte.through
    inlines = [OrtInLine]
    
    index_category = 'Stammdaten'
    
    list_display = ('vorname', 'nachname', 'Ist_Musiker', 'Ist_Autor')
    list_display_links =['vorname','nachname']
    
    fields = ['vorname', 'nachname', 'beschreibung']
    
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
@admin.register(schlagwort, site=miz_site)
class SchlagwortAdmin(MIZModelAdmin):
    class AliasInLine(BaseAliasInline):
        model = schlagwort_alias
        extra = 1
    inlines = [AliasInLine]
    list_display = ['schlagwort', 'alias_string', 'ober_string']
        
    index_category = 'Stammdaten'
    search_fields = ['schlagwort', 'unterbegriffe__schlagwort', 'schlagwort_alias__alias']
    def ober_string(self, obj):
        return str(obj.ober) if obj.ober else ''
    ober_string.short_description = 'Oberbegriff'
        
    def alias_string(self, obj):
        return concat_limit(obj.schlagwort_alias_set.all())
    alias_string.short_description = 'Aliase'
    
@admin.register(spielort, site=miz_site)
class SpielortAdmin(MIZModelAdmin):
    list_display = ['name', 'ort']
    
@admin.register(technik, site=miz_site)
class TechnikAdmin(MIZModelAdmin):
    superuser_only = True
    index_category = 'Archivgut'
    inlines = [BestandInLine]

@admin.register(veranstaltung, site=miz_site)
class VeranstaltungAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = veranstaltung.genre.through
    class BandInLine(BaseTabularInline):
        model = veranstaltung.band.through
        verbose_model = band
    class PersonInLine(BaseTabularInline):
        model = veranstaltung.person.through
        verbose_model = person
    inlines=[GenreInLine, BandInLine, PersonInLine]
    
@admin.register(verlag, site=miz_site)
class VerlagAdmin(MIZModelAdmin):
    list_display = ['verlag_name', 'sitz']
    advanced_search_form = {
        'selects' : ['sitz','sitz__land', 'sitz__bland'], 
        'labels' : {'sitz':'Sitz'}
    }
    
        
@admin.register(video, site=miz_site)
class VideoAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = video.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = video.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = video.person.through
        verbose_model = person
    class MusikerInLine(BaseStackedInline):
        model = video.musiker.through
        verbose_model = musiker
        extra = 0
        filter_horizontal = ['instrument']
        fieldsets = [
            (None, {'fields' : ['musiker']}), 
            ("Instrumente", {'fields' : ['instrument'], 'classes' : ['collapse', 'collapsed']}), 
        ]
    class BandInLine(BaseTabularInline):
        model = video.band.through
        verbose_model = band
    class SpielortInLine(BaseTabularInline):
        model = video.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = video.veranstaltung.through
        verbose_model = veranstaltung
    superuser_only = True
    index_category = 'Archivgut'
    inlines = [BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine, BestandInLine]
        
# ======================================================== Orte ========================================================

@admin.register(bundesland, site=miz_site)
class BlandAdmin(MIZModelAdmin):
    list_display = ['bland_name', 'code', 'land']
    advanced_search_form = {
        'selects' : ['ort__land'], 
    }
    
@admin.register(land, site=miz_site)
class LandAdmin(MIZModelAdmin):
    pass
    
@admin.register(kreis, site=miz_site)
class KreisAdmin(MIZModelAdmin):
    superuser_only = True
    
@admin.register(ort, site=miz_site)
class OrtAdmin(MIZModelAdmin):
    fields = ['stadt', 'land', 'bland']
    index_category = 'Stammdaten'
    
    list_display = ['stadt', 'bland', 'land']
    list_display_links = list_display
    
    advanced_search_form = {
        'selects' : ['land', 'bland']
    }
    
@admin.register(bestand, site=miz_site)
class BestandAdmin(MIZModelAdmin):
    #readonly_fields = ['audio', 'ausgabe', 'ausgabe_magazin', 'bildmaterial', 'buch', 'dokument', 'memorabilien', 'technik', 'video']
    list_display = ['signatur', 'bestand_art', 'lagerort','provenienz']
    #flds_to_group = [('ausgabe', 'ausgabe_magazin')]
    
    superuser_only = True
    advanced_search_form = {
        'selects' : ['bestand_art', 'lagerort'], 
    }
    
@admin.register(datei, site=miz_site)
class DateiAdmin(MIZModelAdmin):
    class GenreInLine(BaseGenreInline):
        model = datei.genre.through
    class SchlInLine(BaseSchlagwortInline):
        model = datei.schlagwort.through
    class PersonInLine(BaseTabularInline):
        model = datei.person.through
        verbose_model = person
    class MusikerInLine(BaseStackedInline):
        model = datei.musiker.through
        verbose_model = musiker
        filter_horizontal = ['instrument']
    class BandInLine(BaseTabularInline):
        model = datei.band.through
        verbose_model = band
    class SpielortInLine(BaseTabularInline):
        model = datei.spielort.through
        verbose_model = spielort
    class VeranstaltungInLine(BaseTabularInline):
        model = datei.veranstaltung.through
        verbose_model = veranstaltung
    superuser_only = True
    index_category = 'Archivgut'
    inlines = [QuelleInLine, BandInLine, MusikerInLine, VeranstaltungInLine, SpielortInLine, GenreInLine, SchlInLine, PersonInLine]
    fieldsets = [
        (None, { 'fields': ['titel', 'media_typ', 'datei_pfad', 'provenienz']}),
        ('Allgemeine Beschreibung', { 'fields' : ['beschreibung', 'quelle', 'sender', 'bemerkungen']}),  
    ]
    save_on_top = True
    collapse_all = True
    hint = 'Diese Seite ist noch nicht vollständig fertig gestellt. Bitte noch nicht benutzen.'
    
@admin.register(instrument, site=miz_site)
class InstrumentAdmin(MIZModelAdmin):
    list_display = ['instrument', 'kuerzel']
    
@admin.register(
    buch_serie, monat, lagerort, geber, sender, sprache, plattenfirma, provenienz, 
    Format, FormatTag, FormatSize, FormatTyp, NoiseRed, 
    site=miz_site
)
class HiddenFromIndex(MIZModelAdmin):
    superuser_only = True

from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
miz_site.register(Group, GroupAdmin)
miz_site.register(User, UserAdmin)
