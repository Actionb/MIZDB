from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.utils import IntegrityError
from django.utils.functional import cached_property

from .base.models import BaseModel, ComputedNameModel, BaseAliasModel
from .constants import *
from .m2m import *
from .utils import concat_limit
from .managers import AusgabeQuerySet

#TODO: fix search_fields order!
#TODO: delete dupe_fields  

class person(ComputedNameModel):
    #TODO: ComputedNameModel + new strat attributes
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(default = 'unbekannt', **CF_ARGS)
    herkunft = models.ForeignKey('ort', null = True,  blank = True,  on_delete=models.PROTECT)
    beschreibung = models.TextField(blank = True)
    
    name_composing_fields = ['vorname', 'nachname']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Person'
        verbose_name_plural = 'Personen'
        ordering = ['nachname', 'vorname', 'herkunft']
    
    def autoren_string(self):
        return concat_limit(self.autor_set.all())
    autoren_string.short_description = 'Als Autoren'
    
    def musiker_string(self):
        return concat_limit(self.musiker_set.all())
    musiker_string.short_description = 'Als Musiker'
    
    @classmethod
    def _get_name(self, **data):
        return "{} {}".format(data.get('vorname', ''), data.get('nachname', '')).strip()
        
#    @classmethod
#    def strquery(cls, search_term, prefix = ''):
#        # search_term will be a name with vor and nachname, we need to split these up
#        qitems_list = []
#        for part in search_term.split():
#            qobject = models.Q()
#            # Get the basic list of qitems from super. Here: one qitem (list) per part in search_term
#            for qitem in super(person, cls).strquery(part, prefix):
#                qitems_list.append(qitem)
#        return qitems_list
#    
    
class musiker(BaseModel): 
    kuenstler_name = models.CharField('Künstlername', **CF_ARGS)
    person = models.ForeignKey(person, null = True, blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_musiker_genre)
    instrument = models.ManyToManyField('instrument',  through = m2m_musiker_instrument)
    beschreibung = models.TextField(blank = True)
    
    search_fields = ['kuenstler_name', 'person__vorname', 'person__nachname', 'musiker_alias__alias']
    primary_search_fields = []
    name_field = 'kuenstler_name'
    search_fields_suffixes = {'person__vorname':'Vorname', 'person__nachname':'Nachname', 'musiker_alias__alias':'Alias'}
    
    #dupe_fields = ['kuenstler_name', 'person']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Musiker'
        verbose_name_plural = 'Musiker'
        ordering = ['kuenstler_name', 'person']
        
    def band_string(self):
        return concat_limit(self.band_set.all())
    band_string.short_description = 'Bands'
    
    def genre_string(self):
        return concat_limit(self.genre.all())
    genre_string.short_description = 'Genres'
    
    def herkunft_string(self):
        if self.person and self.person.herkunft:
            return str(self.person.herkunft)
        else:
            return '---'
    herkunft_string.short_description = 'Herkunft'
class musiker_alias(BaseAliasModel):
    parent = models.ForeignKey('musiker')
    
    
class genre(BaseModel):
    genre = models.CharField('Genre', max_length = 100,   unique = True)
    ober = models.ForeignKey('self', related_name = 'obergenre', verbose_name = 'Oberbegriff', null = True,  blank = True,  on_delete=models.SET_NULL)
    
    search_fields = ['genre', 'obergenre__genre', 'genre_alias__alias']
    primary_search_fields = ['genre']
    name_field = 'genre'
    search_fields_suffixes = {'obergenre__genre': 'Obergenre', 'genre_alias__alias': 'Alias'}
    create_field = 'genre'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
        
    def ober_string(self):
        return self.ober if self.ober else ''
    ober_string.short_description = 'Obergenre'
        
    def alias_string(self):
        return concat_limit(self.genre_alias_set.all())
    alias_string.short_description = 'Aliase'
class genre_alias(BaseAliasModel):
    parent = models.ForeignKey('genre')
        
        
class band(BaseModel):
    band_name = models.CharField('Bandname', **CF_ARGS)
    herkunft = models.ForeignKey('ort', models.PROTECT, null = True,  blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_band_genre)
    musiker = models.ManyToManyField('musiker',  through = m2m_band_musiker)
    beschreibung = models.TextField(blank = True)

    #dupe_fields = ['band_name', 'herkunft_id']
    search_fields = ['band_name','band_alias__alias', 'musiker__kuenstler_name', 'musiker__musiker_alias__alias']
    primary_search_fields = ['band_name', 'band_alias__alias']
    #name_field = 'band_name'
    #search_fields_suffixes = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied', 'musiker__musiker_alias__alias':'Mitglied-Alias'}

    class Meta(BaseModel.Meta):
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']
        
    def genre_string(self):
        return concat_limit(self.genre.all())
    genre_string.short_description = 'Genres'
        
    def musiker_string(self):
        return concat_limit(self.musiker.all())
    musiker_string.short_description = 'Mitglieder'
    
    def alias_string(self):
        return concat_limit(self.band_alias_set.all())
    alias_string.short_description = 'Aliase'
class band_alias(BaseAliasModel):
    parent = models.ForeignKey('band')
  
  
class autor(ComputedNameModel):
    kuerzel = models.CharField('Kürzel', **CF_ARGS_B)
    person = models.ForeignKey('person', on_delete=models.PROTECT)
    magazin = models.ManyToManyField('magazin', blank = True,  through = m2m_autor_magazin)
    
    name_composing_fields = ['person___name', 'kuerzel']
    
    search_fields = ['kuerzel', 'person__vorname', 'person__nachname']
    primary_search_fields = []
    search_fields_suffixes = {}
    
#    dupe_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'
        ordering = ['person__vorname', 'person__nachname']
            
    def magazin_string(self):
        return concat_limit(self.magazin.all())
    magazin_string.short_description = 'Magazin(e)'
    
    @classmethod
    def _get_name(self, **data):
        kuerzel = data.get('kuerzel', '')
        person = data.get('person___name', '')
        if kuerzel:
            return "{} ({})".format(person, kuerzel)
        else:
            return person
            
#TODO: delete me   
#    @classmethod
#    def strquery(cls, search_term, prefix = ''):
#        pattern = re.compile(r'(?P<name>\w+.*\w*).+\((?P<kuerzel>\w+)\)') #-> groups: n:'name',k:'(kuerzel)' from 'name (kuerzel)'
#        regex = re.search(pattern, search_term)
#        # See if the user has used a pattern of "Vorname Nachname (Kuerzel)"
#        if regex:
#            sname = regex.group('name')
#            skuerzel = regex.group('kuerzel')
#            person_sq_list = []
#            # Unpack all q objects from the person.strquery search into a new list
#            for qitem_list in person.strquery(sname, prefix = prefix + 'person__'):
#                for q in qitem_list:
#                    person_sq_list.append(q)
#            return [person_sq_list, [models.Q( (prefix+'kuerzel', skuerzel) )]]
#        else:
#            # search_term will be a name with vor, nachname and possibly kuerzel, we need to split these up
#            qitems_list = []
#            for part in search_term.split():
#                qobject = models.Q()
#                # Get the basic list of qitems from super. Here: one qitem (list) per part in search_term
#                for qitem in super(autor, cls).strquery(part, prefix):
#                    qitems_list.append(qitem)
#            return qitems_list
            
            
class ausgabe(ComputedNameModel):
    STATUS_CHOICES = [('unb','unbearbeitet'), ('iB','in Bearbeitung'), ('abg','abgeschlossen')]
    
    magazin = models.ForeignKey('magazin', verbose_name = 'Magazin', on_delete=models.PROTECT)
    status = models.CharField('Bearbeitungsstatus', max_length = 40, choices = STATUS_CHOICES, default = 1)
    e_datum = models.DateField('Erscheinungsdatum', null = True,  blank = True, help_text = 'Format: tt.mm.jjjj')
    jahrgang = models.PositiveSmallIntegerField(null = True,  blank = True, verbose_name = "Jahrgang")
    info = models.TextField(max_length = 200, blank = True)
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    
    audio = models.ManyToManyField('audio', through = m2m_audio_ausgabe, blank = True)
    
#    dupe_fields = ['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum',
#                    'ausgabe_monat__monat', 'e_datum', 'magazin', 'sonderausgabe']
                    
    search_fields = ['ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 
                    'ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk', 'jahrgang', 'info']
    primary_search_fields = ['_name']
    search_fields_suffixes = {
        'ausgabe_monat__monat__monat':'Monat',
        'ausgabe_lnum__lnum':'lfd. Num', 
        'e_datum':'E.datum', 
        'ausgabe_num__num':'Num', 
        'jahrgang':'Jahrgang', 
        'ausgabe_monat__monat__abk':'Monat Abk.', 
        'ausgabe_jahr__jahr' : 'Jahr', 
        'info' : 'Info-Text', 
        }
    
    objects = AusgabeQuerySet.as_manager()
    
    class Meta(ComputedNameModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin', 'jahrgang']
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
        
    name_composing_fields = [
        'info', 'sonderausgabe', 'e_datum', 'jahrgang', 
        'magazin__ausgaben_merkmal', 'ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat__abk'
    ]
        
    @classmethod
    def _get_name(cls, **data):
        # data provided by values_dict: { key: [value1, value2, ...], ... }
        info = data.get('info', '')
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
                
    def anz_artikel(self):
        return self.artikel_set.count()
    anz_artikel.short_description = 'Anz. Artikel'
    
    def jahre(self):
        return concat_limit(self.ausgabe_jahr_set.all())
    jahre.short_description = 'Jahre'
    
    def num_string(self):
        return concat_limit(self.ausgabe_num_set.all())
    num_string.short_description = 'Nummer'
    
    def lnum_string(self):
        return concat_limit(self.ausgabe_lnum_set.all())
    lnum_string.short_description = 'lfd. Nummer'
    
    def monat_string(self):
        try:
            if self.ausgabe_monat_set.exists():
                return concat_limit([v for v in self.ausgabe_monat_set.values_list('monat__abk', flat=True)])
        except:
            return 'Woops'
    monat_string.short_description = 'Monate'
    
    def zbestand(self):
        try:
            return self.bestand_set.filter(lagerort=lagerort.objects.get(pk=ZRAUM_ID)).exists()
        except:
            return False
    zbestand.short_description = 'Bestand: ZRaum'
    zbestand.boolean = True
    
    def dbestand(self):
        try:
            return self.bestand_set.filter(lagerort=lagerort.objects.get(pk=DUPLETTEN_ID)).exists()
        except:
            return False
    dbestand.short_description = 'Bestand: Dublette'
    dbestand.boolean = True
    
#TODO: delete me            
#    @classmethod
#    def strquery(cls, search_term, prefix = ''):
#        is_num = False
#        rslt = []
#        if "-" in search_term: # nr oder monat: 2001-13
#            try:
#                jahre, details = (search_term.split("-"))
#            except:
#                return []
#            is_num = True
#        elif re.search(r'.\((.+)\)', search_term): # lfd nr: 13 (2001)
#            try:
#                details, jahre = re.search(r'(.*)\((.+)\)', search_term).groups()
#            except:
#                return []
#        else:
#            return []
#            
#        jahre_prefix = jahre[:2]
#        ajahre = []
#        for j in jahre.split("/"):
#            if len(j)<4:
#                if j=='00':
#                    j = '2000'
#                else:
#                    j = jahre_prefix+j
#            ajahre.append(j.strip())
#        details = [d.strip() for d in details.split("/")]
#        
#        rslt = [ [models.Q( (prefix+'ausgabe_jahr__jahr__iexact', j))]  for j in ajahre ]
#        for d in details:
#            qobject = models.Q()
#            if d.isnumeric():
#                if is_num:
#                    qobject |= models.Q( (prefix+'ausgabe_num__num', d) )
#                else:
#                    qobject |= models.Q( (prefix+'ausgabe_lnum__lnum', d) )
#            else:
#                for fld in ['ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk']:
#                    qobject |= models.Q( (prefix+fld, d) )
#            rslt.append([qobject])
#        return rslt
        
        
class ausgabe_jahr(BaseModel):
    JAHR_VALIDATORS = [MaxValueValidator(MAX_JAHR),MinValueValidator(MIN_JAHR)]
    
    jahr = models.PositiveSmallIntegerField('Jahr', validators = JAHR_VALIDATORS)#, default = CUR_JAHR)
    ausgabe = models.ForeignKey('ausgabe')
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        unique_together = ('jahr', 'ausgabe')
        ordering = ['jahr']
        
        
class ausgabe_num(BaseModel):
    num = models.IntegerField('Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)
    ausgabe = models.ForeignKey('ausgabe')
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Nummer'
        verbose_name_plural = 'Ausgabennummer'
        unique_together = ('num', 'ausgabe', 'kuerzel')
        ordering = ['num']
        
        
class ausgabe_lnum(BaseModel):
    lnum = models.IntegerField('Lfd. Nummer')
    kuerzel = models.CharField(**CF_ARGS_B)
    ausgabe = models.ForeignKey('ausgabe')
    
    class Meta(BaseModel.Meta):
        verbose_name = 'lfd. Nummer'
        verbose_name_plural = 'Laufende Nummer'
        unique_together = ('lnum', 'ausgabe', 'kuerzel')
        ordering = ['lnum']
        
        
class ausgabe_monat(BaseModel):
    ausgabe = models.ForeignKey('ausgabe')
    monat = models.ForeignKey('monat')
        
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
    #TODO: remove either info or beschreibung
    TURNUS_CHOICES = [('u', 'unbekannt'), 
        ('t','täglich'), ('w','wöchentlich'), ('w2','zwei-wöchentlich'), ('m','monatlich'), ('m2','zwei-monatlich'), 
        ('q','quartalsweise'), ('hj','halbjährlich'), ('j','jährlich')]
    MERKMAL_CHOICES = [('num', 'Nummer'), ('lnum', 'Lfd.Nummer'), ('monat', 'Monat'), ('e_datum', 'Ersch.Datum')]
    
    magazin_name = models.CharField('Magazin', **CF_ARGS)
    info = models.TextField(blank = True)
    erstausgabe = models.DateField(null = True,  blank = True)
    turnus = models.CharField(choices = TURNUS_CHOICES, default = 'u', **CF_ARGS_B)
    magazin_url = models.URLField(verbose_name = 'Webpage', blank = True)
    beschreibung = models.TextField(blank = True)
    ausgaben_merkmal = models.CharField(choices = MERKMAL_CHOICES, **CF_ARGS_B)
    #NIY: fanzine = models.BooleanField()
    
    verlag = models.ForeignKey('verlag', null = True,  blank = True, on_delete = models.PROTECT)
    genre = models.ManyToManyField('genre', blank = True,  through = m2m_magazin_genre)
    ort = models.ForeignKey('ort', null = True, blank = True, verbose_name = 'Hrsg.Ort', on_delete = models.SET_NULL)
    
    exclude = ['ausgaben_merkmal', 'info', 'magazin_url', 'turnus', 'erstausgabe', 'beschreibung']
    search_fields = ['magazin_name']
    name_field = 'magazin_name'
    create_field = 'magazin_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']
        
    def __str__(self):
        return str(self.magazin_name)
        
    def anz_ausgaben(self):
        return self.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    
    
class verlag(BaseModel):
    verlag_name = models.CharField('verlag', **CF_ARGS)
    sitz = models.ForeignKey('ort',  null = True,  blank = True, on_delete = models.SET_NULL)
    
    name_field = 'verlag_name'
    create_field = 'verlag_name'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


class ort(ComputedNameModel):
    #TODO: ordering looks wrong in dal
    stadt = models.CharField(**CF_ARGS_B)
    bland = models.ForeignKey('bundesland', verbose_name = 'Bundesland',  null = True,  blank = True, on_delete = models.PROTECT)
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    primary_search_fields = []
    search_fields_suffixes = {
        'land__code' : 'Land-Code', 
        'bland__code' : 'Bundesland-Code', 
        'bland__bland_name' : 'Bundesland', 
        'land_name' : 'Land'
    }
    
    name_composing_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    
    class Meta(BaseModel.Meta):
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
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
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
    
    search_fields = ['land_name', 'code']
    primary_search_fields = []
    name_field = 'land_name'
    search_fields_suffixes = {
        'code':'Land-Code'
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']
class land_alias(BaseAliasModel):
    parent = models.ForeignKey('land')

        
class schlagwort(BaseModel):
    schlagwort = models.CharField( max_length = 100,  unique = True)
    ober = models.ForeignKey('self', related_name = 'oberschl', verbose_name = 'Oberbegriff', null = True,  blank = True)
    
    search_fields = ['schlagwort', 'oberschl__schlagwort', 'schlagwort_alias__alias']
    primary_search_fields = []
    name_field = 'schlagwort'
    search_fields_suffixes = {'oberschl__schlagwort': 'Oberbegriff', 'schlagwort_alias__alias': 'Alias'}
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
        
    def ober_string(self):
        return self.ober if self.ober else ''
    ober_string.short_description = 'Oberbegriff'
        
    def num_artikel(self):
        return self.artikel_set.count()
    num_artikel.short_description = 'Anz. Artikel'
        
    def alias_string(self):
        return concat_limit(self.schlagwort_alias_set.all())
    alias_string.short_description = 'Aliase'
class schlagwort_alias(BaseAliasModel):
    parent = models.ForeignKey('schlagwort')
        
        
class artikel(BaseModel):
    F = 'f'
    FF = 'ff'
    SU_CHOICES = [(F, 'f'), (FF, 'ff')]
    
    ausgabe = models.ForeignKey('ausgabe',  on_delete=models.PROTECT)
    schlagzeile = models.CharField(**CF_ARGS)
    seite = models.PositiveSmallIntegerField(verbose_name="Seite")
    seitenumfang = models.CharField(max_length = 3, blank = True,  choices = SU_CHOICES,  default = '')
    zusammenfassung = models.TextField(blank = True)
    info = models.TextField(blank = True)
    
    genre = models.ManyToManyField('genre', through = m2m_artikel_genre, verbose_name='Genre')
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_artikel_schlagwort, verbose_name='Schlagwort')
    person = models.ManyToManyField('person', through = m2m_artikel_person)
    autor = models.ManyToManyField('autor', through = m2m_artikel_autor)
    band = models.ManyToManyField('band', through = m2m_artikel_band)
    musiker = models.ManyToManyField('musiker', through = m2m_artikel_musiker)
    ort = models.ManyToManyField('ort', through = m2m_artikel_ort)
    spielort = models.ManyToManyField('spielort', through = m2m_artikel_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_artikel_veranstaltung)
    
    search_fields = ['schlagzeile', 'zusammenfassung', 'info']
    primary_search_fields = ['schlagzeile']
    name_field = 'schlagzeile'
    search_fields_suffixes = {
        'zusammenfassung' : 'Zusammenfassung', 
        'info' : 'Info-Text'
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
    verlag = models.ForeignKey('verlag', related_name = 'buchverlag',  null = True,  blank = True)
    verlag_orig = models.ForeignKey('verlag', related_name = 'buchverlagorig', verbose_name = 'Verlag (Original)', null = True,  blank = True)
    ausgabe = models.CharField(**CF_ARGS_B)
    auflage = models.CharField(**CF_ARGS_B)
    buch_serie = models.ForeignKey('buch_serie', verbose_name = 'Buchserie', null = True, blank = True)
    buch_band = models.CharField('Buch Band', **CF_ARGS_B)
    sprache = models.ForeignKey('sprache', related_name = 'buchsprache', null = True, blank = True)
    sprache_orig = models.ForeignKey('sprache', related_name = 'buchspracheorig',  verbose_name = 'Sprache (Original)', null = True, blank = True)
    ubersetzer  = models.CharField('Übersetzer', **CF_ARGS_B)
    #NYI: edition = models.CharField(**CF_ARGS_B, choices = EDITION_CHOICES, blank = True)
    EAN = models.CharField(**CF_ARGS_B)
    ISBN = models.CharField(**CF_ARGS_B)
    LCCN = models.CharField(**CF_ARGS_B)
    
    autor = models.ManyToManyField('autor',  through = m2m_buch_autor)
    
    search_fields = ['titel']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {}
    
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
    parent = models.ForeignKey('instrument')
        
        
class audio(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    tracks = models.IntegerField(verbose_name = 'Anz. Tracks', blank = True, null = True)
    laufzeit = models.DurationField(blank = True, null = True)
    e_jahr = models.PositiveSmallIntegerField(verbose_name = 'Erscheinungsjahr', blank = True, null = True)
    quelle = models.CharField(help_text = 'Broadcast, Live, etc.',  **CF_ARGS_B)
    sender = models.ForeignKey('sender',  blank = True,  null = True, help_text = 'Name des Radio-/Fernsehsenders')
    catalog_nr = models.CharField(verbose_name = 'Katalog Nummer', **CF_ARGS_B)
    
    release_id = models.PositiveIntegerField(blank = True,  null = True, verbose_name = "Release ID (discogs)")      #discogs release id (discogs.com/release/1709793)
    discogs_url = models.URLField(verbose_name = "Link discogs.com", blank = True,  null = True)
    
    bemerkungen = models.TextField(blank = True)
    
    plattenfirma = models.ManyToManyField('plattenfirma', through = m2m_audio_plattenfirma)
    band = models.ManyToManyField('band', through = m2m_audio_band)
    genre = models.ManyToManyField('genre', through = m2m_audio_genre)
    musiker = models.ManyToManyField('musiker', through = m2m_audio_musiker)
    person = models.ManyToManyField('person', through = m2m_audio_person)
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_audio_schlagwort)
    spielort = models.ManyToManyField('spielort', through = m2m_audio_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_audio_veranstaltung)
    ort = models.ManyToManyField('ort', through = m2m_audio_ort)
    
    search_fields = ['titel']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {}
    
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
    
    search_fields = ['titel']
    name_field = 'titel'
    
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
    
    search_fields = ['titel']
    name_field = 'titel'
    
    class Meta(BaseModel.Meta):
        ordering = ['titel']
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'
        permissions = [
            ('alter_bestand_dokument', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
    
    
class kreis(BaseModel):
    name = models.CharField(**CF_ARGS)
    bland = models.ForeignKey('bundesland')
    
    class Meta(BaseModel.Meta):
        ordering = ['name', 'bland']
        verbose_name = 'Kreis'
        verbose_name_plural = 'Kreise'
        
        
class memorabilien(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    search_fields = ['titel']
    name_field = 'titel'
    
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
    parent = models.ForeignKey('sender')
    
    
class spielort(BaseModel):
    #TODO: search for ort___name
    name = models.CharField(**CF_ARGS)
    ort = models.ForeignKey('ort')
    
    search_fields = ['name', 'spielort_alias__alias']
    primary_search_fields = ['name']
    search_fields_suffixes = {
        'spielort_alias__alias':'Alias', 
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name']
class spielort_alias(BaseAliasModel):
    parent = models.ForeignKey('spielort')
    
    
class sprache(BaseModel):
    sprache = models.CharField(**CF_ARGS)
    abk = models.CharField(max_length = 3)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Sprache'
        verbose_name_plural = 'Sprachen'
        ordering = ['sprache']
        
    
class technik(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    search_fields = ['name']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_technik', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
    
class veranstaltung(BaseModel):
    name = models.CharField(**CF_ARGS)
    datum = models.DateField()
    spielort = models.ForeignKey('spielort')
    ort = models.ForeignKey('ort',  null = True,  blank = True)
    
    genre = models.ManyToManyField('genre',  through = m2m_veranstaltung_genre)
    person = models.ManyToManyField('person', verbose_name = 'Teilnehmer (Personen)', through = m2m_veranstaltung_person)
    band = models.ManyToManyField('band', verbose_name = 'Teilnehmer (Bands)',  through = m2m_veranstaltung_band)
    #NYI: musiker = models.ManyToManyField('musiker', through = m2m_veranstaltung_musiker)#
    
    search_fields = ['name', 'veranstaltung_alias__alias']
    primary_search_fields = []
    name_field = 'name'
    search_fields_suffixes = {
        'veranstaltung_alias__alias' : 'Alias', 
    }
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'spielort', 'ort', 'datum']
class veranstaltung_alias(BaseAliasModel):
    parent = models.ForeignKey('veranstaltung')


class video(BaseModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()
    laufzeit = models.TimeField()
    festplatte = models.CharField(**CF_ARGS_B)
    quelle = models.CharField(**CF_ARGS_B)
    sender = models.ForeignKey('sender')
    
    band = models.ManyToManyField('band', through = m2m_video_band)
    genre = models.ManyToManyField('genre', through = m2m_video_genre)
    musiker = models.ManyToManyField('musiker', through = m2m_video_musiker)
    person = models.ManyToManyField('person', through = m2m_video_person)
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_video_schlagwort)
    spielort = models.ManyToManyField('spielort', through = m2m_video_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_video_veranstaltung)
    
    search_fields = ['titel']
    primary_search_fields = []
    name_field = 'titel'
    search_fields_suffixes = {}
    
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
    geber = models.ForeignKey('geber')
    typ = models.CharField('Art der Provenienz',  max_length = 100,  choices = TYP_CHOICES,  default = TYP_CHOICES[0][0])
    
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
    signatur = models.AutoField(primary_key=True)
    lagerort = models.ForeignKey('lagerort')
    provenienz = models.ForeignKey('provenienz',  blank = True, null = True)
    
    audio = models.ForeignKey('audio', blank = True, null = True)
    ausgabe = models.ForeignKey('ausgabe', blank = True, null = True)
    bildmaterial = models.ForeignKey('bildmaterial', blank = True, null = True)
    buch = models.ForeignKey('buch', blank = True, null = True)
    dokument = models.ForeignKey('dokument', blank = True, null = True)
    memorabilien = models.ForeignKey('memorabilien', blank = True, null = True)
    technik = models.ForeignKey('technik', blank = True, null = True)
    video = models.ForeignKey('video', blank = True, null = True)
        
    BESTAND_CHOICES = [
        ('audio', 'Audio'), ('ausgabe', 'Ausgabe'), ('bildmaterial', 'Bildmaterial'),  
        ('buch', 'Buch'),  ('dokument', 'Dokument'), ('memorabilien', 'Memorabilien'), 
        ('technik', 'Technik'), ('video', 'Video'), 
    ]      
    bestand_art = models.CharField('Bestand-Art', max_length = 20, choices = BESTAND_CHOICES, blank = False, default = 'ausgabe')
    
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
        
    def ausgabe_magazin(self):
        if self.ausgabe:
            return str(self.ausgabe.magazin)
    ausgabe_magazin.short_description = "Magazin"
    
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
    provenienz = models.ForeignKey('provenienz', on_delete = models.SET_NULL, blank = True, null = True)
    
    # Allgemeine Beschreibung
    beschreibung = models.TextField(blank = True)
    datum = models.DateField(blank = True, null = True) #NOTE: Wird das nicht durch Veranstaltung abgedeckt?
    bemerkungen = models.TextField(blank = True)
    quelle = models.CharField(help_text = "z.B. Broadcast, Live, etc.", **CF_ARGS_B) # z.B. Broadcast, Live, etc.
    sender = models.ForeignKey('sender', on_delete = models.SET_NULL, blank = True,  null = True)
    
    # Relationen
    genre = models.ManyToManyField('genre', through = m2m_datei_genre)
    schlagwort = models.ManyToManyField('schlagwort', through = m2m_datei_schlagwort)
    person = models.ManyToManyField('person', through = m2m_datei_person)
    band = models.ManyToManyField('band', through = m2m_datei_band)
    musiker = models.ManyToManyField('musiker', through = m2m_datei_musiker)
    ort = models.ManyToManyField('ort', through = m2m_datei_ort)
    spielort = models.ManyToManyField('spielort', through = m2m_datei_spielort)
    veranstaltung = models.ManyToManyField('veranstaltung', through = m2m_datei_veranstaltung)
    
    name_field = 'titel'
    
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
    format_typ = models.ForeignKey('FormatTyp', verbose_name = 'Format Typ')
    format_size = models.ForeignKey('FormatSize', verbose_name = 'Format Größe', help_text = 'LP, 12", Mini-Disc, etc.', blank = True,  null = True)
    catalog_nr = models.CharField(verbose_name = "Katalog Nummer", **CF_ARGS_B) 
    tape = models.CharField(**CF_ARGS_B)
    
    channel = models.CharField(choices = CHANNEL_CHOICES, **CF_ARGS_B)
    noise_red = models.ForeignKey('NoiseRed', verbose_name = 'Noise Reduction', on_delete = models.SET_NULL, blank = True, null = True)
    tag = models.ManyToManyField('FormatTag', verbose_name = 'Tags', blank = True) 
    audio = models.ForeignKey('audio')
    
    bemerkungen = models.TextField(blank = True)
    
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

# Testmagazin for... testing
tmag = magazin.objects.get(pk=326)

# from django.conf import settings --> settings.AUTH_USER_MODEL
class Favoriten(models.Model): #NOTE: why not inherit from BaseModel?
    user = models.OneToOneField('auth.User', editable = False)
    fav_genres = models.ManyToManyField('genre', verbose_name = 'Favoriten Genre', blank = True)
    fav_schl = models.ManyToManyField('schlagwort', verbose_name = 'Favoriten Schlagworte', blank = True)
    
    def __str__(self):
        return 'Favoriten von {}'.format(self.user)
    
    def get_favorites(self, model = None):
        rslt = {fld.related_model:getattr(self, fld.name).all() for fld in Favoriten._meta.many_to_many}
        if model:
            return rslt.get(model, Favoriten.objects.none())
        return rslt
    
wip_models = [bildmaterial, buch, dokument, memorabilien, video]
main_models = [artikel, audio, ausgabe, autor, band, bildmaterial, buch, dokument, genre, magazin, memorabilien, musiker, 
                person, schlagwort, video]
# filter out wip models 
main_models = [m._meta.model_name for m in main_models if not m in wip_models]
