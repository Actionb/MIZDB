from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.utils import IntegrityError

from .constants import *
from .m2m import *
from .utils import concat_limit
from .managers import AusgabeQuerySet, MIZQuerySet        

class ShowModel(models.Model):  
    
    exclude = ['info', 'beschreibung', 'bemerkungen']                #field names to exclude from searches
    search_fields = []          #custom list of search fields, largely used for specifying related fields
    primary_fields = []         #fields that have the highest priority for searching and must always be included
    dupe_fields = []            #fields to determine duplicates with
    objects = MIZQuerySet.as_manager()
    
    def _show(self):
        rslt = ""
        for fld in self.get_basefields():
            #TODO: this is a bit outdated perhaps.
            if getattr(self, fld.name):
                rslt +=  "{} ".format(str(getattr(self, fld.name)))
        if rslt:
            return rslt.strip()
        else:
            return "---"
            
    def __str__(self):
        return self._show()
        
    @classmethod
    def get_duplicates(cls):
        # calls get_duplicates in helper.py
        return [i for i in get_duplicates(cls._meta.model.objects, cls.dupe_fields)]
    
    @classmethod
    def get_basefields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields
            if i != cls._meta.pk and not i.is_relation and not i.name in cls.exclude]
        
    @classmethod
    def get_foreignfields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields if isinstance(i, models.ForeignKey) and not i.name in cls.exclude]
        
    @classmethod
    def get_m2mfields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.get_fields() if (not isinstance(i, models.ForeignKey) and i.is_relation) and not i.name in cls.exclude] 
        
    @classmethod
    def get_paths(cls):
        #NOTE: what is even using this?
        rslt = set()
        for fld in cls._meta.get_fields():
            if fld.is_relation:
                rslt.add(fld.get_path_info()[0]) 
        return list(rslt)
        
    @classmethod
    def get_required_fields(cls, as_string=False):
        rslt = []
        for fld in cls._meta.fields:
            if not fld.auto_created and fld.blank == False:
                if not fld.has_default() or fld.get_default() is None: #NOTE: NOT fld.get_default() is None??
                    if as_string:
                        rslt.append(fld.name)
                    else:
                        rslt.append(fld)
        return rslt
        return [i.name if as_string else i for i in cls._meta.fields if not i.auto_created and not i.has_default() and i.blank == False]
    
    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        #TODO: check if all cls.search_fields are of this model
        rslt = set(list(cls.search_fields) + cls.get_basefields(as_string=True))
        if foreign:
            for fld in cls.get_foreignfields():
                for rel_fld in fld.related_model.get_search_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        if m2m:
            for fld in cls.get_m2mfields():
                for rel_fld in fld.related_model.get_search_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        return rslt
        
    def get_updateable_fields(obj):
        rslt = []
        for fld in obj._meta.get_fields():
            if fld.concrete:
                value = fld.value_from_object(obj)
                if value in fld.empty_values:
                    # This field's value is 'empty' in some form or other
                    rslt.append(fld.name)
                else:
                    default = fld.default if not fld.default is models.fields.NOT_PROVIDED else None
                    if not default is None:
                        # fld.default is a non-None value, see if the field's value differs from it
                        if type(default) is bool:
                            # Special case, boolean values should be left alone?
                            continue
                        elif default == value:
                            # This field has it's default value as value:
                            rslt.append(fld.name)
                        elif default in fld.choices and fld.choices[default][0] == value:
                            # This field has it's default choice as a value
                            rslt.append(fld.name)
        return rslt
            
        
    @classmethod
    def strquery(cls, search_term, prefix = ''):
        """     To be implemented by Models that may require a search by __str__ of the model.
                This implementation is just a lazy default!
                Returns a list of lists of Q instances to filter with.  
                        for q in qitems: <--- q is list of Q instances, qitems a list of lists
                            qs = qs.filter(*q)  <--- *q remember unpacking the list                               
        """
        qobject = models.Q()
        for fld in cls.get_search_fields(m2m=False):
            qobject |= models.Q ( (prefix+fld, search_term) )
        return [[qobject]]
        
    @classmethod
    def strquery_as_queryset(cls, search_term, prefix = '', queryset = None):
        """     Much like strquery, but returns a filtered Queryset.
        """
        qs = queryset or cls.objects
        qitems = cls.strquery(search_term, prefix)
        for q in qitems:
            qs = qs.filter(*q)
        return qs
        
    def print_values(self):
        print(self.__str__())
        
    def print_compare(self, compare_to):
        pass
    
    class Meta:
        abstract = True
        default_permissions = ('add', 'change', 'delete', 'merge')
        
class alias_base(ShowModel):
    alias = models.CharField('Alias', max_length = 100)
    parent = None
    class Meta(ShowModel.Meta):
        verbose_name = 'Alias'
        verbose_name = 'Alias'
        abstract = True

# app models

class person(BaseModel):
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(default = 'unbekannt', **CF_ARGS)
    herkunft = models.ForeignKey('ort', null = True,  blank = True,  on_delete=models.PROTECT)
    beschreibung = models.TextField(blank = True)
    
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
    def strquery(cls, search_term, prefix = ''):
        # search_term will be a name with vor and nachname, we need to split these up
        qitems_list = []
        for part in search_term.split():
            qobject = models.Q()
            # Get the basic list of qitems from super. Here: one qitem (list) per part in search_term
            for qitem in super(person, cls).strquery(part, prefix):
                qitems_list.append(qitem)
        return qitems_list

    
class musiker(BaseModel): 
    kuenstler_name = models.CharField('Künstlername', **CF_ARGS)
    person = models.ForeignKey(person, null = True, blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_musiker_genre)
    instrument = models.ManyToManyField('instrument',  through = m2m_musiker_instrument)
    beschreibung = models.TextField(blank = True)
    
    search_fields = ['kuenstler_name', 'person__vorname', 'person__nachname', 'musiker_alias__alias']
    dupe_fields = ['kuenstler_name', 'person']
    
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
        
class musiker_alias(alias_base):
    parent = models.ForeignKey('musiker')
    
    
class genre(BaseModel):
    genre = models.CharField('Genre', max_length = 100,   unique = True)
    ober = models.ForeignKey('self', related_name = 'obergenre', verbose_name = 'Oberbegriff', null = True,  blank = True,  on_delete=models.SET_NULL)
    
    search_fields = ['genre', 'obergenre__genre', 'genre_alias__alias']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
        
    def ober_string(self):
        return self.ober if self.ober else ''
        
    def alias_string(self):
        return concat_limit(self.genre_alias_set.all())
    alias_string.short_description = 'Aliase'
    
class genre_alias(alias_base):
    parent = models.ForeignKey('genre')
        
        
class band(BaseModel):
    band_name = models.CharField('Bandname', **CF_ARGS)
    herkunft = models.ForeignKey('ort', models.PROTECT, null = True,  blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_band_genre)
    musiker = models.ManyToManyField('musiker',  through = m2m_band_musiker)
    beschreibung = models.TextField(blank = True)

    dupe_fields = ['band_name', 'herkunft_id']
    search_fields = ['band_alias__alias', 'musiker__kuenstler_name']

    
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
class band_alias(alias_base):
    parent = models.ForeignKey('band')
    
    
class autor(BaseModel):
    kuerzel = models.CharField('Kürzel', **CF_ARGS_B)
    person = models.ForeignKey('person', on_delete=models.PROTECT)
    magazin = models.ManyToManyField('magazin', blank = True,  through = m2m_autor_magazin)
    
    search_fields = ['person__vorname', 'person__nachname']
    dupe_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Autor'
        verbose_name_plural = 'Autoren'
        ordering = ['person__vorname', 'person__nachname']
        
    def __str__(self):
        if self.kuerzel:
            return "{0} ({1})".format(str(self.person), str(self.kuerzel))
        else:
            return str(self.person)
            
    def magazin_string(self):
        return concat_limit(self.magazin.all())
    magazin_string.short_description = 'Magazin(e)'
    
    @classmethod
    def strquery(cls, search_term, prefix = ''):
        pattern = re.compile(r'(?P<name>\w+.*\w*).+\((?P<kuerzel>\w+)\)') #-> groups: n:'name',k:'(kuerzel)' from 'name (kuerzel)'
        regex = re.search(pattern, search_term)
        # See if the user has used a pattern of "Vorname Nachname (Kuerzel)"
        if regex:
            sname = regex.group('name')
            skuerzel = regex.group('kuerzel')
            person_sq_list = []
            # Unpack all q objects from the person.strquery search into a new list
            for qitem_list in person.strquery(sname, prefix = prefix + 'person__'):
                for q in qitem_list:
                    person_sq_list.append(q)
            return [person_sq_list, [models.Q( (prefix+'kuerzel', skuerzel) )]]
        else:
            # search_term will be a name with vor, nachname and possibly kuerzel, we need to split these up
            qitems_list = []
            for part in search_term.split():
                qobject = models.Q()
                # Get the basic list of qitems from super. Here: one qitem (list) per part in search_term
                for qitem in super(autor, cls).strquery(part, prefix):
                    qitems_list.append(qitem)
            return qitems_list
            
            
class ausgabe(ShowModel):
    STATUS_CHOICES = [('unb','unbearbeitet'), ('iB','in Bearbeitung'), ('abg','abgeschlossen')]
    magazin = models.ForeignKey('magazin', verbose_name = 'Magazin', on_delete=models.PROTECT)
    status = models.CharField('Bearbeitungsstatus', max_length = 40, choices = STATUS_CHOICES, default = 1)
    e_datum = models.DateField('Erscheinungsdatum', null = True,  blank = True, help_text = 'Format: tt.mm.jjjj')
    jahrgang = models.PositiveSmallIntegerField(null = True,  blank = True, verbose_name = "Jahrgang")
    info = models.TextField(max_length = 200, blank = True)
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    
    audio = models.ManyToManyField('audio', through = m2m_audio_ausgabe, blank = True)
    
    dupe_fields = ['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum',
                    'ausgabe_monat__monat', 'e_datum', 'magazin', 'sonderausgabe']
                    
    search_fields = ['ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 
                    'ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk']
    
    objects = AusgabeQuerySet.as_manager()
    class Meta(ShowModel.Meta):
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin', 'jahrgang']
        permissions = [
            ('alter_bestand_ausgabe', 'Aktion: Bestand/Dublette hinzufügen.'), 
            ('alter_data_ausgabe', 'Aktion: Daten verändern.')
        ]
        
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
    
    def save(self, *args, **kwargs):
        super(ausgabe, self).save(*args, **kwargs)
        
        # Use e_datum data to populate month and year sets
        # Note that this can be done AFTER save() as these values are set through RelatedManagers
        self.refresh_from_db()
        if self.e_datum:
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
                    pass
    
    def __str__(self):
        info = concat_limit(str(self.info).split(), width = LIST_DISPLAY_MAX_LEN+5, sep=" ")
        if self.sonderausgabe and self.info:
            return info
        jahre = concat_limit([jahr[2:] if i else jahr for i, jahr in enumerate([str(j.jahr) for j in self.ausgabe_jahr_set.all()])], sep="/")
        if not jahre:
            if self.jahrgang:
                jahre = "Jg.{}".format(str(self.jahrgang))
            else:
                jahre = "k.A." #oder '(Jahr?)'
          
        if self.magazin.ausgaben_merkmal:
        #TODO: not have this return str(None) if ausgaben_merkmal is set but the user does not provide a value
            merkmal = self.magazin.ausgaben_merkmal
            if merkmal == 'e_datum':
                return str(self.e_datum)
            set = getattr(self, 'ausgabe_{}_set'.format(merkmal))
            if set.exists():
                if merkmal == 'monat':
                    return "{0}-{1}".format(jahre,"/".join([str(m.monat.abk) for m in set.all()]))
                if merkmal == 'lnum':
                    if jahre != "k.A.":
                        jahre = " ({})".format(jahre)
                        return concat_limit(set.all(), sep = "/") + jahre
                    else:
                        return concat_limit(set.all(), sep = "/")
                return "{0}-{1}".format(jahre, concat_limit(set.all(), sep = "/", z=2))
                
        num = concat_limit(self.ausgabe_num_set.all(), sep="/", z=2)
        if num:
            return "{0}-{1}".format(jahre, num)
            
        monate = concat_limit(self.ausgabe_monat_set.values_list('monat__abk', flat=True), sep="/")
        if monate:
            return "{0}-{1}".format(jahre, monate)
            
        lnum = concat_limit(self.ausgabe_lnum_set.all(), sep="/", z=2)
        if lnum:
            if jahre == "k.A.":
                return lnum
            else:
                return "{0} ({1})".format(lnum, jahre)
                
        if self.e_datum:
            return str(self.e_datum)
        elif self.info:
            return info
        else:
            return "Keine Angaben zu dieser Ausgabe!"
    
    @classmethod
    def strquery(cls, search_term, prefix = ''):
        is_num = False
        rslt = []
        if "-" in search_term: # nr oder monat: 2001-13
            try:
                jahre, details = (search_term.split("-"))
            except:
                return []
            is_num = True
        elif re.search(r'.\((.+)\)', search_term): # lfd nr: 13 (2001)
            try:
                details, jahre = re.search(r'(.*)\((.+)\)', search_term).groups()
            except:
                return []
        else:
            return []
            
        jahre_prefix = jahre[:2]
        ajahre = []
        for j in jahre.split("/"):
            if len(j)<4:
                if j=='00':
                    j = '2000'
                else:
                    j = jahre_prefix+j
            ajahre.append(j.strip())
        details = [d.strip() for d in details.split("/")]
        
        rslt = [ [models.Q( (prefix+'ausgabe_jahr__jahr__iexact', j))]  for j in ajahre ]
        for d in details:
            qobject = models.Q()
            if d.isnumeric():
                if is_num:
                    qobject |= models.Q( (prefix+'ausgabe_num__num', d) )
                else:
                    qobject |= models.Q( (prefix+'ausgabe_lnum__lnum', d) )
            else:
                for fld in ['ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk']:
                    qobject |= models.Q( (prefix+fld, d) )
            rslt.append([qobject])
        return rslt
        
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
    class Meta(BaseModel.Meta):
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']
        
    search_fields = ['monat__monat', 'monat__abk']
    
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
    
    exclude = ['ausgaben_merkmal', 'info', 'magazin_url', 'turnus', 'erstausgabe']
    
    def anz_ausgaben(self):
        return self.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Magazin'
        verbose_name_plural = 'Magazine'
        ordering = ['magazin_name']

    def __str__(self):
        return str(self.magazin_name)

    def bulk(self, zbestand = True, details = [], dupe_all_sets = False, n_like_m = True, jg = False):
        """
            For creating lots of new issues via Terminal input
        """
        
        while True:
            print("="*20, end="\n\n\n")
            to_create = []
            details = details[:] or ['jahr','num', 'lnum', 'monat']
            if n_like_m:
                if 'num' not in details:
                    n_like_m = False
                    #details.insert(0, 'num')
                elif 'monat' not in details:
                    details.append('monat')
            if 'jahr' not in details:
                details.insert(0,'jahr')
            if jg and 'jahrgang' not in details:
                details.insert(1, 'jahrgang')
            details_dict = {}#{k:[] for k in details}
            max_item_len = {k:len(k) if len(k)>6 else 6 for k in details}
            while True:
                print("Jahr(e):")
                inp = input()
                if inp == 'q':
                    return
                if inp:
                    if any(s in inp for s in ['-']):
                        print("Unerlaubte Zeichen gefunden. Nur ',' und '/' benutzen.")
                        continue
                    inp = inp.replace('/', ',')
                    jahr = inp.split(',')
                    break
                else:
                    jahr = []
                    break
                    print("Mindestens ein Jahr angeben.")
            
            if jahr:
                qs = self.ausgabe_set
                for j in jahr:
                    qs = qs.filter(ausgabe_jahr__jahr=j)
                if qs.exists():
                    print("Bereits vorhandene Ausgaben des Jahres {}:".format(jahr))
                    qs.print_qs()
            
            max_item_len['jahr'] = max(len('jahr')+2, len(str(jahr)))
            if 'jahrgang' in details:
                while True:
                    print("Jahrgang:")
                    inp = input()
                    if inp == 'q':
                        return
                    if inp:
                        try:
                            int(inp)
                        except:
                            print("Bitte nur eine Zahl eingeben.")
                            continue
                    jahrgang = inp
                    max_item_len['jahrgang'] = max(len(jahrgang), len('jahrgang'))
                    break
            
            for k in details:
                if k in ['jahr', 'jahrgang']:
                    continue
                if k == 'monat' and n_like_m and 'num' in details_dict and details_dict['num']:
                    details_dict[k] = details_dict['num'].copy()
                    max_item_len[k] = max_item_len['num']
                    continue
                while True:
                    print(k+":")
                    inp = input()
                    if inp == 'q':
                        return
                    elif inp == '':
                        break
                    elif inp.startswith("="):
                        is_like = inp[1:]
                        if is_like in details_dict and details_dict[is_like]:
                            details_dict[k] = details_dict[is_like].copy()
                            max_item_len[k] = max_item_len[is_like]
                            break
                    temp = []
                    inp = inp.split(',')
                    for item in inp:
                        if item:
                            if item.count('-')==1:# and not any(not i.isnumeric() for i in item.split('-')):
                                if item.count("*") == 1:
                                    item,  multi = item.split("*")
                                    multi = int(multi)
                                else:
                                    multi = 1
                                s, e = (int(i) for i in item.split("-"))
                                
                                for i in range(s, e+1, multi):
                                    temp.append([str(i+j) for j in range(multi)])
                                # 1-10 -> range(1,11)
                                #temp += [str(j) for j in range( *[int(i)+1 if c else int(i) for c, i in enumerate(item.split('-'))] ) ]
                            elif '/' in item:
                                temp.append([i for i in item.split('/') if i])
                            else:
                                temp.append(item)
                    if temp and any(len(temp)!=len(other_list) for x, other_list in details_dict.items() if other_list):
                        print(details_dict)
                        print()
                        print(temp)
                        print('Anzahl der Parameter passt nicht.')
                    else:
                        for item in temp:
                            if len(str(item))>max_item_len[k]:
                                max_item_len[k] = len(str(item))+1
                        details_dict[k] = temp
                        break
                
            if all(len(lst)==0 for lst in details_dict.values()):
                print("Ausgaben benötigen konkrete Angaben!")
                continue
                        
            for index in range(max(map(len, details_dict.values()))):
                ausgabe_dict = {}
                for k in details:
                    try:
                        ausgabe_dict[k] = details_dict[k][index]
                    except:
                        continue
                ausgabe_dict['jahr'] = jahr
                #if 'jahrgang' in details:
                ausgabe_dict['jahrgang'] = jahrgang if 'jahrgang' in details else None
                to_create.append(ausgabe_dict)
            
            # Check for duplicate
            from .utils import print_tabular
            dupe_all = dupe_all_sets or False
            for ausgabe_dict in to_create:
                qs = self.ausgabe_set
                for k, v in ausgabe_dict.items():
                    if k == 'jahrgang':
                        continue
                    x = 'ausgabe_{}'.format(k)
                    x += '__{}'.format(k if k != 'monat' else 'monat_id')
                    if isinstance(v, str):
                        v = [v]
                    for value in v:
                        if value:
                            qs = qs.filter(**{x:value})
                        #NOTE: write a 'matches_X' function, filtering is not the best way for finding duplicates
                if qs.exists():
                    if not dupe_all:
                        print("Ausgabe existiert möglicherweise bereits:")#, [(k, v) for k, v in ausgabe_dict.items()])
                        print("Zu erstellen: ")
                        print_tabular(ausgabe_dict, details)
                        print("\n in Datenbank vorhanden:")
                        qs.print_qs()
                        inp = input("Trotzdem diese Ausgabe erstellen? j/n/q/nn: ")
                        if inp == 'q':
                            return
                        elif inp == 'n':
                            ausgabe_dict['dupe'] = qs
                        elif inp == 'nn':
                            dupe_all = True
                            ausgabe_dict['dupe'] = qs
                        else:
                            ausgabe_dict['dupe'] = None
                    else:
                        ausgabe_dict['dupe'] = qs
                else:
                    ausgabe_dict['dupe'] = None
                    
            # Printing
            print("~"*5,"Ausgaben zu erstellen:", "~"*5, end="\n\n")
            header_string = ""
            for k in details:
                if k in to_create[0].keys():
                    header_string += "|" + k.center(max_item_len[k]) + "|"
            print(header_string)
            print("="*len(header_string))
            for ausgabe_dict in to_create:
                if ausgabe_dict['dupe']:
                    continue
                for k in details:
                    if k in ausgabe_dict.keys():
                        print("|"+str(ausgabe_dict[k]).center(max_item_len[k])+"|", end="")
                print("")
            print("~"*20)
            print("Zraum-Bestand wird automatisch hinzugefügt:", zbestand)
            print("Fortfahren? j/n/q")
            inp = input()
            if inp == 'q':
                return
            if inp == 'n':
                continue
                
            # Saving
            created_instances = []
            for ausgabe_dict in to_create:
                if ausgabe_dict['dupe']:
                    qs = ausgabe_dict['dupe']
                    if qs.count() == 1:
                        instance = qs.first()
                    else:
                        print("Konnte keine eindeutige Ausgabe für {} finden.", ausgabe_dict)
                        continue
                else:
                    if 'jahrgang' in ausgabe_dict and ausgabe_dict['jahrgang']:
                        instance = ausgabe(magazin=self, jahrgang=ausgabe_dict['jahrgang'])
                    else:
                        instance = ausgabe(magazin=self)
                    instance.save()
                    created_instances.append(instance)
                    for k, v in ausgabe_dict.items():
                        if k in ['dupe', 'jahrgang']:
                            continue
                        set = getattr(instance, "ausgabe_{}_set".format(k))
                        if k == 'monat':
                            k = 'monat_id'
                        if isinstance(v, str) or isinstance(v, int):
                            v = [v]
                        for value in v:
                            if value:
                                try:
                                    set.create(**{k:value})
                                except Exception as e:
                                    print(e, v)
                if zbestand:
                    lo = lagerort.objects.get(pk=ZRAUM_ID)
                    set = instance.bestand_set
                    if set.filter(lagerort = lo).exists():
                        lo = lagerort.objects.get(pk=DUPLETTEN_ID)
                        # Dublette
                        try:
                            set.create(ausgabe_id=instance.pk, lagerort = lo)
                        except Exception as e:
                            print(e)
                    else:
                        # Kein Dublette
                        try:
                            set.create(ausgabe_id=instance.pk, lagerort = lo)
                        except Exception as e:
                            print(e)
                if ausgabe_dict['dupe']:
                    print(instance, 'Bestand hinzugefügt!', instance.bestand_set.last())#lagerort.objects.get(pk=ZRAUM_ID))
                else:
                    print(instance, 'erstellt!', bestand.objects.filter(ausgabe_id=instance.pk).first().lagerort)
            
            print("Wie fortfahren? q - Beenden, l - zuletzt erstellte Ausgaben löschen, any - weitere Ausgaben erstellen.")
            inp = input()
            if inp == 'l':
                for instance in created_instances:
                    instance_string = instance.__str__()
                    instance.delete()
                    print(instance_string, 'gelöscht!')
            if inp == 'q':
                return
    
class verlag(BaseModel):
    verlag_name = models.CharField('verlag', **CF_ARGS)
    sitz = models.ForeignKey('ort',  null = True,  blank = True, on_delete = models.SET_NULL)
    class Meta(BaseModel.Meta):
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


class ort(BaseModel):
    stadt = models.CharField(**CF_ARGS_B)
    bland = models.ForeignKey('bundesland', verbose_name = 'Bundesland',  null = True,  blank = True, on_delete = models.PROTECT)
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
    search_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Ort'
        verbose_name_plural = 'Orte'
        unique_together = ('stadt', 'bland', 'land')
        ordering = ['land','bland', 'stadt']
        
    def __str__(self):
        codes = self.land.code
        if self.bland:
            if self.stadt:
                codes += '-' + self.bland.code
                return "{0}, {1}".format(self.stadt,  codes)
            else:
                return str(self.bland.bland_name) + ', ' + codes
        else:
            if self.stadt:
                return str(self.stadt) + ', ' + codes
            else:
                return str(self.land.land_name)
            
        
class bundesland(BaseModel):
    bland_name = models.CharField('Bundesland', **CF_ARGS)
    code = models.CharField(max_length = 4,  unique = False)
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
    search_fields = ['bland_name', 'code']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Bundesland'
        verbose_name_plural = 'Bundesländer'
        unique_together = ('bland_name', 'land')
        ordering = ['land', 'bland_name']                
        
        
class land(BaseModel):
    land_name = models.CharField('Land', max_length = 100,  unique = True)
    code = models.CharField(max_length = 4,  unique = True)
    
    search_fields = ['land_name', 'code']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']
class land_alias(alias_base):
    parent = models.ForeignKey('land')

        
class schlagwort(BaseModel):
    schlagwort = models.CharField( max_length = 100,  unique = True)
    ober = models.ForeignKey('self', related_name = 'oberschl', verbose_name = 'Oberbegriff', null = True,  blank = True)
    
    search_fields = ['schlagwort', 'oberschl__schlagwort', 'schlagwort_alias__alias']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
        
    def ober_string(self):
        return self.ober if self.ober else ''
        
    def num_artikel(self):
        return self.artikel_set.count()
        
    def alias_string(self):
        return concat_limit(self.schlagwort_alias_set.all())
    alias_string.short_description = 'Aliase'
        
class schlagwort_alias(alias_base):
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
    
    #exclude = [seite, seitenumfang, zusammenfassung, info]
    
    search_fields = {'schlagzeile', 'zusammenfassung', 'seite', 'seitenumfang', 'info'}

    
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
    
    search_fields = ['instrument', 'kuerzel']
    
    def __str__(self):
        return str(self.instrument) + " ({})".format(str(self.kuerzel)) if self.kuerzel else str(self.instrument)
    
    class Meta(BaseModel.Meta):
        ordering = ['instrument', 'kuerzel']
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'
class instrument_alias(alias_base):
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
    
    class Meta(BaseModel.Meta):
        ordering = ['serie']
        verbose_name = 'Buchserie'
        verbose_name_plural = 'Buchserien'
        
        
class dokument(BaseModel):
    titel = models.CharField(**CF_ARGS)
    
    search_fields = ['titel']
    
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
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']
        permissions = [
            ('alter_bestand_memorabilien', 'Aktion: Bestand/Dublette hinzufügen.'), 
        ]
        
        
class sender(BaseModel):
    name = models.CharField(**CF_ARGS)
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Sender'
        verbose_name_plural = 'Sender'
        ordering = ['name']
class sender_alias(alias_base):
    parent = models.ForeignKey('sender')
    
    
class spielort(BaseModel):
    name = models.CharField(**CF_ARGS)
    ort = models.ForeignKey('ort')
    
    search_fields = ['name']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name']
class spielort_alias(alias_base):
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
    
    search_fields = ['name']
    
    class Meta(BaseModel.Meta):
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'spielort', 'ort', 'datum']
class veranstaltung_alias(alias_base):
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
    name = models.CharField(default = 'unbekannt', **CF_ARGS)
    
    class Meta(BaseModel.Meta):
        ordering = ['name']
        verbose_name = 'Geber'
        verbose_name_plural = 'Geber'
        
class lagerort(BaseModel):
    ort = models.CharField(**CF_ARGS)
    raum = models.CharField(**CF_ARGS_B)
    regal = models.CharField(**CF_ARGS_B)
    
    signatur = models.CharField(**CF_ARGS_B) # NOTE: use? maybe for human-readable shorthand?
    class Meta(BaseModel.Meta):
        verbose_name = 'Lagerort'
        verbose_name_plural = 'Lagerorte'
        ordering = ['ort']
        
    def __str__(self):
        if self.signatur:
            return str(self.signatur)
        rslt = '{raum}-{regal} ({ort})'
        if not str(self.raum) or not str(self.regal):
            rslt = rslt.replace('-', '').strip()
        if not str(self.raum):
            rslt = rslt.replace('{raum}', '').strip()
        if not str(self.regal):
            rslt = rslt.replace('{regal}', '').strip()
        if rslt.startswith('('):
            rslt = rslt[1:-1]
        return rslt.format(raum=self.raum, regal=self.regal, ort=self.ort)
        
        
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
    
    def __str__(self):
        return str(self.tag)
        
    class Meta(BaseModel.Meta):
        ordering = ['tag']
        verbose_name = 'Format-Tag'
        verbose_name_plural = 'Format-Tags'
        
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
