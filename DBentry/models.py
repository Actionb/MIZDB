from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.utils import IntegrityError
from django.utils.functional import cached_property

from .base.models import BaseModel, ComputedNameModel, BaseAliasModel
from .fields import ISSNField
from .constants import *
from .m2m import *
from .utils import concat_limit
from .managers import AusgabeQuerySet

class person(ComputedNameModel):
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(default = 'unbekannt', **CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Person')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    orte = models.ManyToManyField('ort', blank = True)
    
    name_composing_fields = ['vorname', 'nachname']
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Person'
        verbose_name_plural = 'Personen'
    
    @classmethod
    def _get_name(cls, **data):
        name = "{} {}".format(data.get('vorname', ''), data.get('nachname', '')).strip()
        if name:
            return name
        return cls._name_default % {'verbose_name':cls._meta.verbose_name}
        
        
class musiker(BaseModel): 
    kuenstler_name = models.CharField('Künstlername', **CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Musikers')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    person = models.ForeignKey(person, models.SET_NULL, null = True, blank = True)
    
    genre = models.ManyToManyField('genre',  through = m2m_musiker_genre)
    instrument = models.ManyToManyField('instrument',  through = m2m_musiker_instrument)
    orte = models.ManyToManyField('ort', blank = True)
    
    search_fields = ['kuenstler_name', 'person__vorname', 'person__nachname', 'musiker_alias__alias', 'beschreibung']
    primary_search_fields = []
    name_field = 'kuenstler_name'
    search_fields_suffixes = {'person__vorname':'Vorname', 'person__nachname':'Nachname', 'musiker_alias__alias':'Alias'}
    create_field = 'kuenstler_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        ordering = ['kuenstler_name', 'person']
class musiker_alias(BaseAliasModel):
    parent = models.ForeignKey('musiker', models.CASCADE)
    
    
class genre(BaseModel):
    genre = models.CharField('Genre', max_length = 100,   unique = True)
    
    ober = models.ForeignKey('self', models.SET_NULL, related_name = 'sub_genres', verbose_name = 'Oberbegriff', 
        null = True,  blank = True,
    )
    
    search_fields = ['genre', 'ober__genre', 'sub_genres__genre', 'genre_alias__alias']
    primary_search_fields = ['genre']
    name_field = 'genre'
    search_fields_suffixes = {'ober__genre': 'Subgenre', 'sub_genres__genre' : 'Oberbegriff', 'genre_alias__alias': 'Alias'}
    create_field = 'genre'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
class genre_alias(BaseAliasModel):
    parent = models.ForeignKey('genre', models.CASCADE)
        
        
class band(BaseModel):
    band_name = models.CharField('Bandname', **CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Band')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    genre = models.ManyToManyField('genre',  through = m2m_band_genre)
    musiker = models.ManyToManyField('musiker',  through = m2m_band_musiker)
    orte = models.ManyToManyField('ort', blank = True)

    search_fields = ['band_name','band_alias__alias', 'musiker__kuenstler_name', 'musiker__musiker_alias__alias', 'beschreibung']
    primary_search_fields = ['band_name', 'band_alias__alias']
    name_field = 'band_name'
    search_fields_suffixes = {
        'band_alias__alias':'Band-Alias', 
        'musiker__kuenstler_name':'Band-Mitglied', 
        'musiker__musiker_alias__alias':'Mitglied-Alias', 
        'beschreibung' : 'Beschreibung'
    }
    create_field = 'band_name'

    class Meta(BaseModel.Meta):
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']
class band_alias(BaseAliasModel):
    parent = models.ForeignKey('band', models.CASCADE)
  
  
class autor(ComputedNameModel):
    kuerzel = models.CharField('Kürzel', **CF_ARGS_B)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Autors')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    person = models.ForeignKey('person', models.PROTECT)
    
    magazin = models.ManyToManyField('magazin', blank = True,  through = m2m_autor_magazin)
    orte = models.ManyToManyField('ort', blank = True)
    
    search_fields = ['kuerzel', 'person___name', 'beschreibung']
    primary_search_fields = []
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    name_composing_fields = ['person___name', 'kuerzel']
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'
    
    @classmethod
    def _get_name(cls, **data):
        #TODO: revisit this after person refactor: include a check to ignore a default name for an 'unknown' person
        kuerzel = data.get('kuerzel', '')
        person = data.get('person___name', '')
        if kuerzel:
            return "{} ({})".format(person, kuerzel)
        else:
            return person
            
            
class ausgabe(ComputedNameModel):
    STATUS_CHOICES = [('unb','unbearbeitet'), ('iB','in Bearbeitung'), ('abg','abgeschlossen'), ('kB', 'keine Bearbeitung vorgesehen')]

    status = models.CharField('Bearbeitungsstatus', max_length = 40, choices = STATUS_CHOICES, default = 1)
    e_datum = models.DateField('Erscheinungsdatum', null = True,  blank = True, help_text = 'Format: tt.mm.jjjj')
    jahrgang = models.PositiveSmallIntegerField(null = True,  blank = True, verbose_name = "Jahrgang")
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Ausgabe')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    magazin = models.ForeignKey('magazin', models.PROTECT, verbose_name = 'Magazin')
    
    audio = models.ManyToManyField('audio', through = m2m_audio_ausgabe, blank = True)
                 
    search_fields = [
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 
        'ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk', 'jahrgang', 'beschreibung'
    ]
    primary_search_fields = ['_name']
    search_fields_suffixes = {
        'ausgabe_monat__monat__monat':'Monat',
        'ausgabe_lnum__lnum':'lfd. Num', 
        'e_datum':'E.datum', 
        'ausgabe_num__num':'Num', 
        'jahrgang':'Jahrgang', 
        'ausgabe_monat__monat__abk':'Monat Abk.', 
        'ausgabe_jahr__jahr' : 'Jahr', 
        'beschreibung' : 'Beschreibung', 
        }
        
    name_composing_fields = [
        'beschreibung', 'sonderausgabe', 'e_datum', 'jahrgang', 
        'magazin__ausgaben_merkmal', 'ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat__abk'
    ]   
    
    objects = AusgabeQuerySet.as_manager()
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin', 'jahrgang'] # TODO: revisit ordering
        permissions = [
            ('alter_bestand_ausgabe', 'Aktion: Bestand/Dublette hinzufügen.'), 
            ('alter_data_ausgabe', 'Aktion: Daten verändern.')
        ]
        
    def save(self, *args, **kwargs):
        pre_save_datum = self.e_datum
        super(ausgabe, self).save(update = False, *args, **kwargs)
        
        # Use e_datum data to populate month and year sets
        # Note that this can be done AFTER save() as these values are set through RelatedManagers
        self.refresh_from_db(fields=['e_datum'])
        if self.e_datum != pre_save_datum:
            #NOTE: if we have set ausgabe_jahr from data gathered from e_datum in a previous save, and e_datum changes... ausgabe_jahr will still contain the old's e_datum data
            if self.e_datum.year not in self.ausgabe_jahr_set.values_list('jahr', flat=True):
                self.ausgabe_jahr_set.create(jahr=self.e_datum.year)
            if self.e_datum.month not in self.ausgabe_monat_set.values_list('monat_id', flat=True):
                #NOTE: this actually raised an IntegrityError (UNIQUE Constraints)
                # self.ausgabe_monat_set will be empty but creating a new set instance will still fail
                # need to find out how to reliably reproduce this
                # Maybe this was fixed by overriding validate_unique in FormBase?
                try:
                    self.ausgabe_monat_set.create(monat_id=self.e_datum.month)
                except IntegrityError:
                    # UNIQUE constraint violation, ignore
                    pass
        # parameters that make up the name may have changed, update name accordingly
        self.update_name(force_update = True)
        
    @classmethod
    def _get_name(cls, **data):
        # data provided by values_dict: { key: [value1, value2, ...], ... }
        info = data.get('beschreibung', '')
        info = concat_limit(info.split(), width = LIST_DISPLAY_MAX_LEN+5, sep=" ")
        if data.get('sonderausgabe', False) and info:
            return info
        
        jahre = data.get('ausgabe_jahr__jahr', [])
        jahre = [str(jahr)[2:] if i else str(jahr) for i, jahr in enumerate(jahre)]
        jahre = concat_limit(jahre, sep="/")
        jahrgang = data.get('jahrgang', '')
        
        if not jahre:
            if jahrgang:
                jahre = "Jg. {}".format(jahrgang)
            else:
                jahre = "k.A."
                
        e_datum = data.get('e_datum', '')
        monate = concat_limit(data.get('ausgabe_monat__monat__abk', []), sep="/")
        lnums = concat_limit(data.get('ausgabe_lnum__lnum', []), sep="/", z=2)
        nums = concat_limit(data.get('ausgabe_num__num', []), sep="/", z=2)
        merkmal = data.get('magazin__ausgaben_merkmal', '')
        
        if merkmal:
            if  merkmal == 'e_datum' and e_datum:
                return str(e_datum)
            elif merkmal == 'monat' and monate:
                return "{}-{}".format(jahre, monate)
            elif merkmal == 'lnum' and lnums:
                    if jahre == "k.A.":
                        return lnums
                    else:
                        return "{} ({})".format(lnums, jahre)
            elif nums:
                return "{}-{}".format(jahre, nums)
                
        if nums:
            return "{}-{}".format(jahre, nums)
        if lnums:
            if jahre == "k.A.":
                return lnums
            else:
                return "{} ({})".format(lnums, jahre)
        if e_datum:
            return str(e_datum)
        if monate:
            return "{}-{}".format(jahre, monate)
        if info:
            return info
        return cls._name_default % {'verbose_name':cls._meta.verbose_name}
    
        
class ausgabe_jahr(BaseModel):
    JAHR_VALIDATORS = [MaxValueValidator(MAX_JAHR),MinValueValidator(MIN_JAHR)]
    
    jahr = models.PositiveSmallIntegerField('Jahr', validators = JAHR_VALIDATORS)
    
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        unique_together = ('jahr', 'ausgabe')
        ordering = ['jahr']
        
        
class ausgabe_num(BaseModel):
    num = models.IntegerField('Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)
    
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Nummer'
        verbose_name_plural = 'Ausgabennummer'
        unique_together = ('num', 'ausgabe', 'kuerzel')
        ordering = ['num']
        
        
class ausgabe_lnum(BaseModel):
    lnum = models.IntegerField('Lfd. Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)
    
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'lfd. Nummer'
        verbose_name_plural = 'Laufende Nummer'
        unique_together = ('lnum', 'ausgabe', 'kuerzel')
        ordering = ['lnum']
        
        
class ausgabe_monat(BaseModel):
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE)
    monat = models.ForeignKey('monat', models.CASCADE)
        
    search_fields = ['monat__monat', 'monat__abk']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']
    
    
class monat(BaseModel):
    monat = models.CharField('Monat', **CF_ARGS)
    abk = models.CharField('Abk',  **CF_ARGS)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['id']
        
        
class magazin(BaseModel):
    TURNUS_CHOICES = [('u', 'unbekannt'), 
        ('t','täglich'), ('w','wöchentlich'), ('w2','zwei-wöchentlich'), ('m','monatlich'), ('m2','zwei-monatlich'), 
        ('q','quartalsweise'), ('hj','halbjährlich'), ('j','jährlich')]
    MERKMAL_CHOICES = [('num', 'Nummer'), ('lnum', 'Lfd.Nummer'), ('monat', 'Monat'), ('e_datum', 'Ersch.Datum')]
    
    magazin_name = models.CharField('Magazin', **CF_ARGS)
    erstausgabe = models.DateField(null = True,  blank = True, help_text = 'Format: tt.mm.jjjj')
    turnus = models.CharField(choices = TURNUS_CHOICES, default = 'u', **CF_ARGS_B)
    magazin_url = models.URLField(verbose_name = 'Webpage', blank = True)
    ausgaben_merkmal = models.CharField('Ausgaben Merkmal', help_text = 'Das dominante Merkmal der Ausgaben', choices = MERKMAL_CHOICES, **CF_ARGS_B)
    fanzine = models.BooleanField(default = False)
    issn = ISSNField(blank = True)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Magazines')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    verlag = models.ForeignKey('verlag', models.SET_NULL, null = True,  blank = True)
    ort = models.ForeignKey('ort', models.SET_NULL, null = True, blank = True, verbose_name = 'Hrsg.Ort')
    
    genre = models.ManyToManyField('genre', blank = True,  through = m2m_magazin_genre)
    
    #exclude = ['ausgaben_merkmal', 'magazin_url', 'turnus', 'erstausgabe', 'beschreibung']
    search_fields = ['magazin_name', 'beschreibung']
    name_field = 'magazin_name'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    create_field = 'magazin_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']
        
    def __str__(self):
        return str(self.magazin_name)
    
    
class verlag(BaseModel):
    verlag_name = models.CharField('verlag', **CF_ARGS)
    
    sitz = models.ForeignKey('ort', models.SET_NULL, null = True,  blank = True)
    
    search_fields = ['verlag_name', 'sitz___name', 'sitz__land__land_name', 'sitz__bland__bland_name']
    name_field = 'verlag_name'
    create_field = 'verlag_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


class ort(ComputedNameModel):
    stadt = models.CharField(**CF_ARGS_B)
    
    bland = models.ForeignKey('bundesland', models.SET_NULL, verbose_name = 'Bundesland',  null = True,  blank = True)
    land = models.ForeignKey('land', models.PROTECT, verbose_name = 'Land')
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    primary_search_fields = []
    search_fields_suffixes = {
        'land__code' : 'Land-Code', 
        'bland__code' : 'Bundesland-Code', 
        'bland__bland_name' : 'Bundesland', 
        'land_name' : 'Land'
    }
    
    name_composing_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ort'
        verbose_name_plural = 'Orte'
        unique_together = ('stadt', 'bland', 'land')
        ordering = ['land','bland', 'stadt']
        
    @classmethod
    def _get_name(cls, **data):
        stadt = data.get('stadt', '')
        bundesland = data.get('bland__bland_name', '')
        bundesland_code = data.get('bland__code', '')
        land = data.get('land__land_name', '')
        land_code = data.get('land__code', '')
        
        rslt_template = "{}, {}"
        
        if stadt:
            if bundesland_code:
                codes = land_code + '-' + bundesland_code
                return rslt_template.format(stadt, codes)
            else:
                return rslt_template.format(stadt, land_code)
        else:
            if bundesland:
                return rslt_template.format(bundesland, land_code)
            else:
                return land
            
        
class bundesland(BaseModel):
    bland_name = models.CharField('Bundesland', **CF_ARGS)
    code = models.CharField(max_length = 4,  unique = False)
    
    land = models.ForeignKey('land', models.PROTECT, verbose_name = 'Land')
    
    search_fields = ['bland_name', 'code']
    primary_search_fields = []
    name_field = 'bland_name'
    search_fields_suffixes = {
        'code':'Bundesland-Code'
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Bundesland'
        verbose_name_plural = 'Bundesländer'
        unique_together = ('bland_name', 'land')
        ordering = ['land', 'bland_name']                
        
        
class land(BaseModel):
    land_name = models.CharField('Land', max_length = 100,  unique = True)
    code = models.CharField(max_length = 4,  unique = True)
    
    search_fields = ['land_name', 'code', 'land_alias__alias']
    primary_search_fields = ['land_name', 'code']
    name_field = 'land_name'
    search_fields_suffixes = {
        'code':'Land-Code', 
        'land_alias__alias' : 'Land-Alias', 
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']
class land_alias(BaseAliasModel):
    parent = models.ForeignKey('land', models.CASCADE)

        
class schlagwort(BaseModel):
    schlagwort = models.CharField( max_length = 100,  unique = True)
    
    ober = models.ForeignKey('self', models.SET_NULL, related_name = 'unterbegriffe', verbose_name = 'Oberbegriff', null = True,  blank = True)
    
    search_fields = ['schlagwort', 'unterbegriffe__schlagwort', 'ober__schlagwort', 'schlagwort_alias__alias']
    primary_search_fields = []
    name_field = 'schlagwort'
    search_fields_suffixes = {'unterbegriffe__schlagwort': 'Oberbegriff', 'ober__schlagwort' : 'Unterbegriff', 'schlagwort_alias__alias': 'Alias'}
    create_field = 'schlagwort'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
class schlagwort_alias(BaseAliasModel):
    parent = models.ForeignKey('schlagwort', models.CASCADE)
        
        
class artikel(BaseModel):
    F = 'f'
    FF = 'ff'
    SU_CHOICES = [(F, 'f'), (FF, 'ff')]
    
    schlagzeile = models.CharField(**CF_ARGS)
    seite = models.PositiveSmallIntegerField(verbose_name="Seite")
    seitenumfang = models.CharField(max_length = 3, blank = True,  choices = SU_CHOICES,  default = '')
    zusammenfassung = models.TextField(blank = True)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Artikels')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    ausgabe = models.ForeignKey('ausgabe', models.PROTECT)
    
    genre = models.ManyToManyField('genre', through = m2m_artikel_genre, verbose_name='Genre')
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_artikel_schlagwort, verbose_name='Schlagwort')
    person = models.ManyToManyField('person', through = m2m_artikel_person)
    autor = models.ManyToManyField('autor', through = m2m_artikel_autor)
    band = models.ManyToManyField('band', through = m2m_artikel_band)
    musiker = models.ManyToManyField('musiker', through = m2m_artikel_musiker)
    ort = models.ManyToManyField('ort', through = m2m_artikel_ort)
    spielort = models.ManyToManyField('spielort', through = m2m_artikel_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_artikel_veranstaltung)
    
    search_fields = ['schlagzeile', 'zusammenfassung', 'beschreibung']
    primary_search_fields = ['schlagzeile']
    name_field = 'schlagzeile'
    search_fields_suffixes = {
        'zusammenfassung' : 'Zusammenfassung', 
        'beschreibung' : 'Beschreibung'
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Artikel'
        verbose_name_plural = 'Artikel'
        ordering = ['seite','ausgabe','pk']
        
    def __str__(self):
        if self.schlagzeile:
            return str(self.schlagzeile)
        elif self.zusammenfassung:
            return str(self.zusammenfassung)
        else:
            return 'Keine Schlagzeile gegeben!'
    
    def zusammenfassung_string(self):
        if not self.zusammenfassung:
            return ''
        return concat_limit(self.zusammenfassung.split(), sep=" ")
    zusammenfassung_string.short_description = 'Zusammenfassung'
    
    def artikel_magazin(self):
        return self.ausgabe.magazin
    artikel_magazin.short_description = 'Magazin'
    
    def schlagwort_string(self):
        return concat_limit(self.schlagwort.all())
    schlagwort_string.short_description = 'Schlagwörter'
    
    def kuenstler_string(self):
        return concat_limit(list(self.band.all()) + list(self.musiker.all()))
    kuenstler_string.short_description = 'Künstler'
        

class buch(BaseModel):
    titel = models.CharField(**CF_ARGS)
    titel_orig = models.CharField('Titel (Original)', **CF_ARGS_B)
    jahr = models.PositiveIntegerField(**YF_ARGS)
    jahr_orig = models.PositiveIntegerField('Jahr (Original)',**YF_ARGS)
    ausgabe = models.CharField(**CF_ARGS_B)
    auflage = models.CharField(**CF_ARGS_B)
    buch_band = models.CharField('Buch Band', **CF_ARGS_B)
    ubersetzer  = models.CharField('Übersetzer', **CF_ARGS_B)
    #edition = models.CharField(**CF_ARGS_B)
    EAN = models.CharField(**CF_ARGS_B)
    ISBN = models.CharField(**CF_ARGS_B)
    LCCN = models.CharField(**CF_ARGS_B)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Buches')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    buch_serie = models.ForeignKey('buch_serie', models.SET_NULL, verbose_name = 'Buchserie', null = True, blank = True)
    verlag = models.ForeignKey('verlag', models.SET_NULL, null = True,  blank = True)
    verlag_orig = models.ForeignKey('verlag', models.SET_NULL, related_name = 'buch_orig_set', verbose_name = 'Verlag (Original)', null = True,  blank = True)
    sprache = models.ForeignKey('sprache', models.SET_NULL, null = True, blank = True)
    sprache_orig = models.ForeignKey('sprache', models.SET_NULL, related_name = 'buch_orig_set', verbose_name = 'Sprache (Original)', null = True, blank = True)
    
    autor = models.ManyToManyField('autor')
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Buch'
        verbose_name_plural = 'Bücher'
        permissions = [
            ('alter_bestand_buch', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    def __str__(self):
        return str(self.titel)
    

class instrument(BaseModel):
    instrument = models.CharField(unique = True, **CF_ARGS)
    kuerzel = models.CharField(verbose_name = 'Kürzel', **CF_ARGS) 
    
    search_fields = ['instrument', 'instrument_alias__alias', 'kuerzel']
    primary_search_fields = ['instrument']
    name_field = 'instrument'
    search_fields_suffixes = {
        'instrument_alias__alias' : 'Alias', 
        'kuerzel' : 'Kürzel'
    }
    
    class Meta(BaseModel.Meta):
        ordering = ['instrument', 'kuerzel']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'
    
    def __str__(self):
        return str(self.instrument) + " ({})".format(str(self.kuerzel)) if self.kuerzel else str(self.instrument)
class instrument_alias(BaseAliasModel):
    parent = models.ForeignKey('instrument', models.CASCADE)
        
        
class audio(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    tracks = models.IntegerField(verbose_name = 'Anz. Tracks', blank = True, null = True)
    laufzeit = models.DurationField(blank = True, null = True)
    e_jahr = models.PositiveSmallIntegerField(verbose_name = 'Erscheinungsjahr', blank = True, null = True)
    quelle = models.CharField(help_text = 'Broadcast, Live, etc.',  **CF_ARGS_B)
    catalog_nr = models.CharField(verbose_name = 'Katalog Nummer', **CF_ARGS_B)
    release_id = models.PositiveIntegerField(blank = True,  null = True, verbose_name = "Release ID (discogs)")      #discogs release id (discogs.com/release/1709793)
    discogs_url = models.URLField(verbose_name = "Link discogs.com", blank = True,  null = True)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Mediums')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    sender = models.ForeignKey('sender', models.SET_NULL, blank = True,  null = True, help_text = 'Name des Radio-/Fernsehsenders')
    
    plattenfirma = models.ManyToManyField('plattenfirma', through = m2m_audio_plattenfirma)
    band = models.ManyToManyField('band', through = m2m_audio_band)
    genre = models.ManyToManyField('genre', through = m2m_audio_genre)
    musiker = models.ManyToManyField('musiker', through = m2m_audio_musiker)
    person = models.ManyToManyField('person', through = m2m_audio_person)
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_audio_schlagwort)
    spielort = models.ManyToManyField('spielort', through = m2m_audio_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_audio_veranstaltung)
    ort = models.ManyToManyField('ort', through = m2m_audio_ort)
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Audio Material'
        verbose_name_plural = 'Audio Materialien'
        permissions = [
            ('alter_bestand_audio', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    def __str__(self):
        return str(self.titel)
        
    def save(self, *args, **kwargs):
        if self.release_id:
            self.discogs_url = "http://www.discogs.com/release/" + str(self.release_id)
        else:
            self.discogs_url = None
        super(audio, self).save(*args, **kwargs)
        
    def kuenstler_string(self):
        return concat_limit(list(self.band.all()) + list(self.musiker.all()))
    kuenstler_string.short_description = 'Künstler'
    
    def formate_string(self):
        return concat_limit(list(self.format_set.all()))
    formate_string.short_description = 'Format'
    
    
class bildmaterial(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Bildmaterials')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Bild Material'
        verbose_name_plural = 'Bild Materialien'
        permissions = [
            ('alter_bestand_bildmaterial', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
        
class buch_serie(BaseModel):
    serie = models.CharField(**CF_ARGS)
    
    search_fields = ['serie']
    name_field = 'serie'
    
    class Meta(BaseModel.Meta):
        ordering = ['serie']
        verbose_name = 'Buchserie'
        verbose_name_plural = 'Buchserien'
        
        
class dokument(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Dokumentes')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'
        permissions = [
            ('alter_bestand_dokument', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
    
    
class kreis(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    bland = models.ForeignKey('bundesland', models.CASCADE)
    
    class Meta(BaseModel.Meta):
        ordering = ['name', 'bland']
        verbose_name = 'Kreis'
        verbose_name_plural = 'Kreise'
        
        
class memorabilien(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Memorabiliums')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_memorabilien', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
        
class sender(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    create_field = 'name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Sender'
        verbose_name_plural = 'Sender'
        ordering = ['name']
class sender_alias(BaseAliasModel):
    parent = models.ForeignKey('sender', models.CASCADE)
    
    
class spielort(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    ort = models.ForeignKey('ort', models.PROTECT)
    
    search_fields = ['name', 'spielort_alias__alias', 'ort___name']
    primary_search_fields = ['name']
    name_field = 'name'
    search_fields_suffixes = {
        'spielort_alias__alias':'Alias', 
        'ort___name' : 'Ort', 
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name']
class spielort_alias(BaseAliasModel):
    parent = models.ForeignKey('spielort', models.CASCADE)
    
    
class sprache(BaseModel):
    sprache = models.CharField(**CF_ARGS)
    abk = models.CharField(max_length = 3)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Sprache'
        verbose_name_plural = 'Sprachen'
        ordering = ['sprache']
        
    
class technik(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Technik')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_technik', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    
class veranstaltung(BaseModel):
    name = models.CharField(**CF_ARGS)
    datum = models.DateField(help_text = 'Format: tt.mm.jjjj')
    
    spielort = models.ForeignKey('spielort', models.PROTECT)
    
    genre = models.ManyToManyField('genre')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    schlagwort = models.ManyToManyField('schlagwort')
    musiker = models.ManyToManyField('musiker')
    
    search_fields = ['name', 'veranstaltung_alias__alias']
    primary_search_fields = []
    name_field = 'name'
    search_fields_suffixes = {
        'veranstaltung_alias__alias' : 'Alias', 
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'spielort', 'datum']
class veranstaltung_alias(BaseAliasModel):
    parent = models.ForeignKey('veranstaltung', models.CASCADE)


class video(BaseModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()
    laufzeit = models.TimeField()
    festplatte = models.CharField(**CF_ARGS_B)
    quelle = models.CharField(**CF_ARGS_B)
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Mediums')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    sender = models.ForeignKey('sender', models.SET_NULL, blank = True,  null = True)
    
    band = models.ManyToManyField('band')
    genre = models.ManyToManyField('genre')
    musiker = models.ManyToManyField('musiker', through = m2m_video_musiker)
    person = models.ManyToManyField('person')
    schlagwort = models.ManyToManyField('schlagwort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Video Material'
        verbose_name_plural = 'Video Materialien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_video', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    
class provenienz(BaseModel):
    SCHENK = 'Schenkung'
    SPENDE = 'Spende'
    FUND = 'Fund'
    LEIHG = 'Leihgabe'
    DAUERLEIHG = 'Dauerleihgabe'
    TYP_CHOICES = [(SCHENK, 'Schenkung'), (SPENDE, 'Spende'), (FUND,'Fund'), (LEIHG, 'Leihgabe'), (DAUERLEIHG,'Dauerleihgabe')]
    
    typ = models.CharField('Art der Provenienz',  max_length = 100,  choices = TYP_CHOICES,  default = TYP_CHOICES[0][0])
    
    geber = models.ForeignKey('geber', models.PROTECT)
    
    search_fields = ['geber__name']
    
    class Meta(BaseModel.Meta):
        ordering = ['geber', 'typ']
        verbose_name = 'Provenienz'
        verbose_name_plural = 'Provenienzen'
        
    def __str__(self):
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))
        
        
class geber(BaseModel):
    #TODO: merge with person?
    name = models.CharField(default = 'unbekannt', **CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Geber'
        verbose_name_plural = 'Geber'
        
class lagerort(ComputedNameModel):
    ort = models.CharField(**CF_ARGS)
    raum = models.CharField(**CF_ARGS_B)
    regal = models.CharField(**CF_ARGS_B)
    
    name_composing_fields = ['ort', 'raum', 'regal']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['ort']
        
    @classmethod
    def _get_name(cls, **data):
        ort = data.get('ort')
        raum = data.get('raum', '')
        regal = data.get('regal', '')
        
        if raum:
            if regal:
                return "{}-{} ({})".format(raum, regal, ort)
            else:
                return "{} ({})".format(raum, ort)
        elif regal:
            return "{} ({})".format(regal, ort)
        else:
            return ort
        
        
class bestand(BaseModel):
    BESTAND_CHOICES = [
        ('audio', 'Audio'), ('ausgabe', 'Ausgabe'), ('bildmaterial', 'Bildmaterial'),  
        ('buch', 'Buch'),  ('dokument', 'Dokument'), ('memorabilien', 'Memorabilien'), 
        ('technik', 'Technik'), ('video', 'Video'), 
    ]  
    signatur = models.AutoField(primary_key=True)
    bestand_art = models.CharField('Bestand-Art', max_length = 20, choices = BESTAND_CHOICES, blank = False, default = 'ausgabe')
    
    lagerort = models.ForeignKey('lagerort', models.PROTECT)
    provenienz = models.ForeignKey('provenienz', models.SET_NULL, blank = True, null = True)
    
    audio = models.ForeignKey('audio', models.CASCADE, blank = True, null = True)
    ausgabe = models.ForeignKey('ausgabe', models.CASCADE, blank = True, null = True)
    bildmaterial = models.ForeignKey('bildmaterial', models.CASCADE, blank = True, null = True)
    buch = models.ForeignKey('buch', models.CASCADE, blank = True, null = True)
    dokument = models.ForeignKey('dokument', models.CASCADE, blank = True, null = True)
    memorabilien = models.ForeignKey('memorabilien', models.CASCADE, blank = True, null = True)
    technik = models.ForeignKey('technik', models.CASCADE, blank = True, null = True)
    video = models.ForeignKey('video', models.CASCADE, blank = True, null = True)    
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Bestand'
        verbose_name_plural = 'Bestände'
        ordering = ['pk']

    def __str__(self):
        return str(self.lagerort)
        
    def bestand_objekt(self):
        #TODO: WIP create a template just for bestand changeform so we can display the object in question as a link
        #art = self.bestand_art(as_field = True)
        objekt = art.value_from_object(self)
    
    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        # Find the correct Bestand-Art
        for fld_name, choice in self.BESTAND_CHOICES:
            if getattr(self, fld_name):
                self.bestand_art = fld_name
        super(bestand, self).save(force_insert, force_update, using, update_fields)

    
class datei(BaseModel):
    
    MEDIA_TYP_CHOICES = [('audio', 'Audio'), ('video', 'Video'), ('bild', 'Bild'), ('text', 'Text'), ('sonstige', 'Sonstige')]
    
    titel = models.CharField(**CF_ARGS)
    media_typ = models.CharField(choices = MEDIA_TYP_CHOICES, verbose_name = 'Media Typ', default = 'audio', **CF_ARGS)
    datei_media = models.FileField(verbose_name = 'Datei', blank = True,  null = True, editable = False, 
            help_text = "Datei auf Datenbank-Server hoch- bzw herunterladen.") #Datei Media Server
    datei_pfad = models.CharField(verbose_name = 'Datei-Pfad', 
            help_text = "Pfad (inklusive Datei-Namen und Endung) zur Datei im gemeinsamen Ordner.", **CF_ARGS_B)
    
    # Allgemeine Beschreibung
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Datei')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    quelle = models.CharField(help_text = "z.B. Broadcast, Live, etc.", **CF_ARGS_B) # z.B. Broadcast, Live, etc.
    
    sender = models.ForeignKey('sender', models.SET_NULL, blank = True,  null = True)
    provenienz = models.ForeignKey('provenienz', models.SET_NULL, blank = True, null = True)
    
    # Relationen
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker', through = m2m_datei_musiker)
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Datei'
        verbose_name_plural = 'Dateien'
        
    def __str__(self):
        return str(self.titel)

  
class Format(BaseModel):
    CHANNEL_CHOICES = [('Stereo', 'Stereo'), ('Mono', 'Mono'), ('Quad', 'Quadraphonic'), 
                        ('Ambi', 'Ambisonic'), ('Multi', 'Multichannel')]
    
    format_name = models.CharField(editable = False, **CF_ARGS_B)
    anzahl = models.PositiveSmallIntegerField(default = 1)
    catalog_nr = models.CharField(verbose_name = "Katalog Nummer", **CF_ARGS_B) 
    tape = models.CharField(**CF_ARGS_B)
    channel = models.CharField(choices = CHANNEL_CHOICES, **CF_ARGS_B)
    bemerkungen = models.TextField(blank = True)
    
    noise_red = models.ForeignKey('NoiseRed', models.SET_NULL, verbose_name = 'Noise Reduction', blank = True, null = True)
    audio = models.ForeignKey('audio', models.CASCADE)
    format_typ = models.ForeignKey('FormatTyp', models.PROTECT, verbose_name = 'Format Typ')
    format_size = models.ForeignKey('FormatSize', models.SET_NULL, verbose_name = 'Format Größe', help_text = 'LP, 12", Mini-Disc, etc.', blank = True,  null = True)
    
    tag = models.ManyToManyField('FormatTag', verbose_name = 'Tags', blank = True) 
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Format'
        verbose_name_plural = 'Formate'
        
    def get_name(self):
        format_string = "{qty}{format}{tags}{channel}"
        return format_string.format(**{
            'qty' : str(self.anzahl)+'x' if self.anzahl > 1 else '', 
            'format' : str(self.format_size) if self.format_size else str(self.format_typ), 
            'tags' : ", " + concat_limit(self.tag.all()) if self.pk and self.tag.exists() else '', 
            'channel' : ", " + self.channel if self.channel else ''
        }).strip()
                
    def __str__(self):
        # This might be super slow
        # update format_name whenever a change is detected
        old_val = self.format_name
        self.format_name = self.get_name()
        if old_val != self.format_name:
            Format.objects.filter(pk=self.pk).update(format_name=self.format_name)
        return self.format_name
        
    def save(self, *args, **kwargs):
        super(Format, self).save(*args, **kwargs)
        self.refresh_from_db()
        self.format_name = self.get_name() 
        Format.objects.filter(pk=self.pk).update(format_name=self.format_name)
        
class NoiseRed(BaseModel):
    verfahren = models.CharField(**CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['verfahren']
        verbose_name = 'Noise Reduction Verfahren'
        verbose_name_plural = 'Noise Reduction Verfahren'

class FormatTag(BaseModel):
    tag = models.CharField(**CF_ARGS)
    abk = models.CharField(verbose_name = 'Abkürzung', **CF_ARGS_B)
    
    class Meta(BaseModel.Meta):
        ordering = ['tag']
        verbose_name = 'Format-Tag'
        verbose_name_plural = 'Format-Tags'
        
    def __str__(self):
        return str(self.tag)
        
        
class FormatSize(BaseModel):
    size = models.CharField(**CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['size']
        verbose_name = 'Format-Größe'
        verbose_name_plural = 'Format-Größen'
            
class FormatTyp(BaseModel):
    """ Art des Formats (Vinyl, DVD, Cassette, etc) """
    typ = models.CharField(**CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['typ']
        verbose_name = 'Format-Typ'
        verbose_name_plural = 'Format-Typen'

class plattenfirma(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Plattenfirma'
        verbose_name_plural = 'Plattenfirmen'


class Favoriten(models.Model): #NOTE: why not inherit from BaseModel?
    user = models.OneToOneField('auth.User', models.CASCADE, editable = False)
    fav_genres = models.ManyToManyField('genre', verbose_name = 'Favoriten Genre', blank = True)
    fav_schl = models.ManyToManyField('schlagwort', verbose_name = 'Favoriten Schlagworte', blank = True)
    
    def __str__(self):
        return 'Favoriten von {}'.format(self.user)
    
    def get_favorites(self, model = None):
        rslt = {fld.related_model:getattr(self, fld.name).all() for fld in Favoriten._meta.many_to_many}
        if model:
            return rslt.get(model, Favoriten.objects.none())
        return rslt
        
    @classmethod
    def get_favorite_models(cls):
        return [fld.related_model for fld in cls._meta.many_to_many]
