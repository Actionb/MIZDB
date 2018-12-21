from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator

from .base.models import (
    BaseModel, ComputedNameModel, BaseAliasModel, AbstractJahrModel, AbstractURLModel
)
from .fields import ISSNField, ISBNField, EANField
from .constants import *
from .m2m import *
from .utils import concat_limit
from .managers import AusgabeQuerySet

#TODO: allow searching by ISSN

class person(ComputedNameModel):
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(**CF_ARGS)
    
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
        return name or cls._name_default % {'verbose_name':cls._meta.verbose_name}
        
        
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
    
    person = models.ForeignKey(
        'person', models.SET_NULL, null = True, blank = True, 
        help_text = "Zur Schnell-Erstellung bitte folgendes Format benutzen: Nachname(n), Vorname(n)"
    )
    
    magazin = models.ManyToManyField('magazin', blank = True,  through = m2m_autor_magazin)
    
    search_fields = ['kuerzel', 'person___name', 'beschreibung']
    primary_search_fields = []
    search_fields_suffixes = {'beschreibung' : 'Beschreibung'}
    
    name_composing_fields = ['person___name', 'kuerzel']
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'
    
    @classmethod
    def _get_name(cls, **data):
        kuerzel = data.get('kuerzel', '')
        person_name = data.get('person___name', '')
        if person_name == person._name_default % {'verbose_name':person._meta.verbose_name} or person_name == 'unbekannt': 
            # person_name is a default value ('unbekannt' used to be the default for person__nachname)
            person_name = ''
            
        if person_name:
            if kuerzel:
                return "{} ({})".format(person_name, kuerzel)
            else:
                return person_name
        else:
            return kuerzel or cls._name_default % {'verbose_name':cls._meta.verbose_name}
            
            
class ausgabe(ComputedNameModel):
    STATUS_CHOICES = [('unb','unbearbeitet'), ('iB','in Bearbeitung'), ('abg','abgeschlossen'), ('kB', 'keine Bearbeitung vorgesehen')]

    status = models.CharField('Bearbeitungsstatus', max_length = 40, choices = STATUS_CHOICES, default = 1)
    e_datum = models.DateField('Erscheinungsdatum', null = True,  blank = True, help_text = 'Format: tt.mm.jjjj')
    jahrgang = models.PositiveSmallIntegerField(null = True,  blank = True, verbose_name = "Jahrgang",  validators = [MinValueValidator(1)])
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Ausgabe')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    magazin = models.ForeignKey('magazin', models.PROTECT, verbose_name = 'Magazin')
    
    audio = models.ManyToManyField('audio', through = m2m_audio_ausgabe, blank = True)
                 
    search_fields = [
        'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 'e_datum', 
        'ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk', 'jahrgang', 'beschreibung', 'bemerkungen'
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
        'bemerkungen': 'Bemerkungen', 
        }
        
    name_composing_fields = [
        'beschreibung', 'sonderausgabe', 'e_datum', 'jahrgang', 
        'magazin__ausgaben_merkmal', 'ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat__abk'
    ]   
    
    objects = AusgabeQuerySet.as_manager()
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin']
        permissions = [
            ('alter_bestand_ausgabe', 'Aktion: Bestand/Dublette hinzufügen.'), 
            ('alter_data_ausgabe', 'Aktion: Daten verändern.')
        ]
        
    @classmethod
    def _get_name(cls, **data):
        # data provided by values_dict: { key: [value1, value2, ...], ... }
        beschreibung = data.get('beschreibung', '')
        beschreibung = concat_limit(beschreibung.split(), width = LIST_DISPLAY_MAX_LEN+5, sep=" ")
        if data.get('sonderausgabe', False) and beschreibung:
            return beschreibung
        
        jahre = sorted(data.get('ausgabe_jahr__jahr', []))
        jahre = [str(jahr)[2:] if i else str(jahr) for i, jahr in enumerate(jahre)]
        jahre = concat_limit(jahre, sep="/")
        jahrgang = data.get('jahrgang', '')
        
        if not jahre:
            if jahrgang:
                jahre = "Jg. {}".format(jahrgang)
            else:
                jahre = "k.A."
                
        e_datum = data.get('e_datum', '')
        monat_ordering = ['Jan', 'Feb', 'Mrz', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        monate = sorted(
            data.get('ausgabe_monat__monat__abk', []), 
            key = lambda abk: monat_ordering.index(abk)+1 if abk in monat_ordering else 0
        )
        monate = concat_limit(monate, sep="/")
        lnums = concat_limit(sorted(data.get('ausgabe_lnum__lnum', [])), sep="/", z=2)
        nums = concat_limit(sorted(data.get('ausgabe_num__num', [])), sep="/", z=2)
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
        if beschreibung:
            return beschreibung
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
        verbose_name = 'Ausgabe-Monat'
        verbose_name_plural = 'Ausgabe-Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']
        
    def __str__(self):
        return self.monat.abk
    
    
class monat(BaseModel):
    monat = models.CharField('Monat', **CF_ARGS)
    abk = models.CharField('Abk',  **CF_ARGS)
    ordinal = models.PositiveSmallIntegerField(editable = False)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['ordinal']
        
    def __str__(self):
        return self.monat
        
        
class magazin(BaseModel):
    TURNUS_CHOICES = [('u', 'unbekannt'), 
        ('t','täglich'), ('w','wöchentlich'), ('w2','zwei-wöchentlich'), ('m','monatlich'), ('m2','zwei-monatlich'), 
        ('q','quartalsweise'), ('hj','halbjährlich'), ('j','jährlich')]
    MERKMAL_CHOICES = [('num', 'Nummer'), ('lnum', 'Lfd.Nummer'), ('monat', 'Monat'), ('e_datum', 'Ersch.Datum')]
    
    magazin_name = models.CharField('Magazin', **CF_ARGS)
    erstausgabe = models.CharField(**CF_ARGS_B)
    turnus = models.CharField(choices = TURNUS_CHOICES, default = 'u', **CF_ARGS_B)
    magazin_url = models.URLField(verbose_name = 'Webpage', blank = True)
    ausgaben_merkmal = models.CharField('Ausgaben Merkmal', help_text = 'Das dominante Merkmal der Ausgaben', choices = MERKMAL_CHOICES, **CF_ARGS_B)
    fanzine = models.BooleanField('Fanzine', default = False)
    issn = ISSNField('ISSN', blank = True) #NOTE: implement this as reverse foreign relation so one magazin can have multiple ISSN numbers?
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Magazines')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    ort = models.ForeignKey('ort', models.SET_NULL, null = True, blank = True, verbose_name = 'Hrsg.Ort', help_text = 'Angabe für auf eine Region beschränktes Magazin.')
    
    genre = models.ManyToManyField('genre', blank = True,  through = m2m_magazin_genre)
    
    search_fields = ['magazin_name', 'beschreibung', 'issn']
    name_field = 'magazin_name'
    search_fields_suffixes = {'beschreibung' : 'Beschreibung', 'issn':'ISSN'}
    create_field = 'magazin_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']
        
    def __str__(self):
        return str(self.magazin_name)
    
    
class verlag(BaseModel):
    verlag_name = models.CharField('Verlag', **CF_ARGS)
    
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
    
    def __str__(self):
        return "{} {}".format(self.bland_name, self.code).strip()
    
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
    
    def __str__(self):
        return "{} {}".format(self.land_name, self.code).strip()
    
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
        

class buch(BaseModel):
    titel = models.CharField(**CF_ARGS)
    titel_orig = models.CharField('Titel (Original)', **CF_ARGS_B)
    seitenumfang = models.PositiveSmallIntegerField(blank = True, null = True)
    jahr = models.PositiveIntegerField(**YF_ARGS)
    jahr_orig = models.PositiveIntegerField('Jahr (Original)',**YF_ARGS)
    auflage = models.CharField(**CF_ARGS_B)
    EAN = EANField(blank = True)
    ISBN = ISBNField(blank = True)
    is_buchband = models.BooleanField(default = False, verbose_name = 'Ist Sammelband', help_text = 'Dieses Buch ist ein Sammelband bestehend aus Aufsätzen.')
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Buches')
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    schriftenreihe = models.ForeignKey('schriftenreihe', models.SET_NULL, null = True, blank = True)
    buchband = models.ForeignKey(
        'self', models.PROTECT, null = True,  blank = True, limit_choices_to = {'is_buchband':True}, 
        related_name = 'buch_set', help_text = 'Der Sammelband, der diesen Aufsatz enthält.', 
        verbose_name = 'Sammelband', 
    )
    verlag = models.ForeignKey('verlag', models.SET_NULL, null = True,  blank = True)
    sprache = models.ForeignKey('sprache', models.SET_NULL, null = True, blank = True)
    
    herausgeber = models.ManyToManyField('Herausgeber')
    autor = models.ManyToManyField('autor', 
        help_text = "Zur Schnell-Erstellung bitte folgendes Format benutzen: Nachname(n), Vorname(n) (Kürzel)")
    genre = models.ManyToManyField('genre')
    schlagwort = models.ManyToManyField('schlagwort')
    person = models.ManyToManyField('person')
    band = models.ManyToManyField('band')
    musiker = models.ManyToManyField('musiker')
    ort = models.ManyToManyField('ort')
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    search_fields = ['titel', 'beschreibung', 'ISBN', 'EAN']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {
        'beschreibung' : 'Beschreibung', 
        'ISBN' : 'ISBN', 
        'EAN' : 'EAN', 
    }
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Buch'
        verbose_name_plural = 'Bücher'
        permissions = [
            ('alter_bestand_buch', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    def __str__(self):
        return str(self.titel)
        
class Herausgeber(ComputedNameModel):
    person = models.ForeignKey('person', blank = True, null = True)
    organisation = models.ForeignKey('Organisation', blank = True, null = True)
    
    name_composing_fields = ['person___name', 'organisation__name']    
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Herausgeber'
        verbose_name_plural = 'Herausgeber'
    
    @classmethod
    def _get_name(cls, **data):
        person = data.get('person___name', '')
        organisation = data.get('organisation__name', '')
        if person:
            if organisation:
                return "{} ({})".format(person, organisation)
            return person
        return organisation
    
        
class Organisation(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    name_field = 'name'
    create_field = 'name'
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Organisation'
        verbose_name_plural = 'Organisationen'
        

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
    laufzeit = models.DurationField(blank = True, null = True, help_text = 'Format: hh:mm:ss')
    e_jahr = models.PositiveSmallIntegerField(verbose_name = 'Erscheinungsjahr', blank = True, null = True)
    quelle = models.CharField(help_text = 'Broadcast, Live, etc.',  **CF_ARGS_B)
    catalog_nr = models.CharField(verbose_name = 'Katalog Nummer', **CF_ARGS_B)
    release_id = models.PositiveIntegerField(blank = True,  null = True, verbose_name = "Release ID (discogs)")
    discogs_url = models.URLField(verbose_name = "Link discogs.com", blank = True,  null = True, validators = [RegexValidator(discogs_release_id_pattern, message= "Bitte nur Adressen von discogs.com eingeben.")]) #TODO: is null = True a good idea for URLFields?
    
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
        
class schriftenreihe(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    search_fields = ['name']
    name_field = 'name'
    create_field = 'name'
    
    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Schriftenreihe'
        verbose_name_plural = 'Schriftenreihen'
        
        
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
    
    def __str__(self):
        return "{} ({})".format(self.name, str(self.datum))
        
        
class veranstaltung_alias(BaseAliasModel):
    parent = models.ForeignKey('veranstaltung', models.CASCADE)


class video(BaseModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()
    laufzeit = models.DurationField(blank = True, null = True, help_text = 'Format: hh:mm:ss')
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
    fach = models.CharField(**CF_ARGS_B)
    ordner = models.CharField(**CF_ARGS_B)
    
    name_composing_fields = ['ort', 'raum', 'regal', 'fach']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['ort']
        
    @classmethod
    def _get_name(cls, **data):
        ort = data.get('ort')
        raum = data.get('raum', '')
        regal = data.get('regal', '')
        fach = data.get('fach', '')
        
        if regal and fach:
            regal = "{}-{}".format(regal, fach)
        if raum:
            if regal:
                regal = "{}-{}".format(raum, regal)
            else:
                return "{} ({})".format(raum, ort)
        if regal:
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
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, blank = True, null = True)
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

  
class Format(ComputedNameModel):
    CHANNEL_CHOICES = [('Stereo', 'Stereo'), ('Mono', 'Mono'), ('Quad', 'Quadraphonic'), 
                        ('Ambi', 'Ambisonic'), ('Multi', 'Multichannel')]
    
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
    
    name_composing_fields = [
        'anzahl', 'format_size__size', 'format_typ__typ', 'tag__tag', 'channel', 
    ]
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Format'
        verbose_name_plural = 'Formate'
        
    @classmethod
    def _get_name(cls, **data):
        if data.get('anzahl', 0) > 1:
            qty = str(data.get('anzahl')) + 'x'
        else:
            qty = ''
        
        if data.get('format_size__size'):
            format = str(data.get('format_size__size'))
        else:
            format = str(data.get('format_typ__typ'))
            
        if data.get('tag__tag'):
            tags = ", " + concat_limit(sorted(data.get('tag__tag')))
        else:
            tags = ''
            
        if data.get('channel'):
            channel = ", " + data.get('channel')
        else:
            channel = ''
        return qty + format + tags + channel
        
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
       
class BrochureYear(AbstractJahrModel):
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, related_name = 'jahre', blank = True, null = True)
    
class BrochureURL(AbstractURLModel):
    brochure = models.ForeignKey('BaseBrochure', models.CASCADE, related_name = 'urls', blank = True, null = True)
    
class BaseBrochure(BaseModel):
    titel = models.CharField(**CF_ARGS)
    zusammenfassung = models.TextField(blank = True)
    bemerkungen = models.TextField(blank = True, help_text ='Kommentare für Archiv-Mitarbeiter')
    
    ausgabe = models.ForeignKey('ausgabe', models.SET_NULL, related_name = 'beilagen', verbose_name = 'Ausgabe', blank = True, null = True)
    
    genre = models.ManyToManyField('genre')
    
    name_field = 'titel'
    
    #TODO: add verbose_name as this base model's meta options are actually being used (where exactly? if it's just the permission __str__ then we dont need a verbose_name)
    def __str__(self):
        return str(self.titel)
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
    
class Brochure(BaseBrochure):
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. der Broschüre')
    
    schlagwort = models.ManyToManyField('schlagwort')
    
    class Meta(BaseBrochure.Meta):
        verbose_name = 'Broschüre'
        verbose_name_plural = 'Broschüren'
    
class Kalendar(BaseBrochure):
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Programmheftes')
    
    spielort = models.ManyToManyField('spielort')
    veranstaltung = models.ManyToManyField('veranstaltung')
    
    class Meta(BaseBrochure.Meta):
        verbose_name = 'Programmheft'
        verbose_name_plural = 'Programmhefte'
    
class Katalog(BaseBrochure):
    ART_CHOICES = [('merch', 'Merchandise'), ('tech', 'Technik'), ('ton', 'Tonträger')]
    
    beschreibung = models.TextField(blank = True, help_text = 'Beschreibung bzgl. des Kataloges')
    
    art = models.CharField('Art d. Kataloges', max_length = 40, choices = ART_CHOICES, default = 1)
    
    class Meta(BaseBrochure.Meta):
        verbose_name = 'Warenkatalog'
        verbose_name_plural = 'Warenkataloge'
    
    
class Favoriten(models.Model): 
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
