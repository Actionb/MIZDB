from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.utils import IntegrityError

from .constants import *
from .m2m import *
from .utils import concat_limit, merge as merge_util
from .managers import AusgabeQuerySet, MIZQuerySet

# Create your models here.
#TODO: models/m2m change or remove unique_together of m2m-tables to avoid form errors
# let the form save and THEN remove duplicate entries
# OR: delete m2m instances first, then save the new ones?

class ShowModel(models.Model):
    
    exclude = []                #fields to exclude from searches
    search_fields = []          #custom list of search fields, ignores get_search_fields()
    primary_fields = []         #fields that have the highest priority for searching and must always be included
    dupe_fields = []            #fields to determine duplicates with
    objects = MIZQuerySet.as_manager()
            
    def _show(self):
        rslt = ""
        for fld in self.get_basefields():
            if getattr(self, fld.name):
                rslt +=  "{} ".format(str(getattr(self, fld.name)))
        return rslt.strip()
            
    def __str__(self):
        return self._show()
    
#    @classmethod
#    def get_ordering(cls):
#        return cls._meta.ordering
        
    @classmethod
    def get_duplicates(cls):
        # calls get_duplicates in helper.py
        return [i for i in get_duplicates(cls._meta.model.objects, cls.dupe_fields)]
    
    @classmethod
    def get_basefields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields
            if i != cls._meta.pk and not i.is_relation and not i in cls.exclude]
        
    @classmethod
    def get_foreignfields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.fields if isinstance(i, models.ForeignKey) and not i in cls.exclude]
        
    @classmethod
    def get_m2mfields(cls, as_string=False):
        return [i.name if as_string else i for i in cls._meta.get_fields() if (not isinstance(i, models.ForeignKey) and i.is_relation) and not i in cls.exclude] 
    
    @classmethod
    def get_primary_fields(cls, reevaluate=False):
        if cls.primary_fields and not reevaluate:
            return [fld if isinstance(fld, str) else fld.name for fld in cls.primary_fields]
        else:
            return cls.get_basefields(as_string=True)
    
    @classmethod
    def get_search_fields(cls, foreign=True, m2m=True, reevaluate=False):
        if cls.search_fields and not reevaluate:
            return cls.search_fields
        rslt = set(cls.get_primary_fields() + cls.get_basefields(as_string=True))
        if foreign:
            for fld in cls.get_foreignfields():
                for rel_fld in fld.related_model.get_primary_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        if m2m:
            for fld in cls.get_m2mfields():
                for rel_fld in fld.related_model.get_primary_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        return rslt
    
    @classmethod
    def resolve_search_fields(cls, fieldlist):
        search_fields = cls.get_search_fields()
        rslt = []
        # Wrangle fieldlist into being a list of string field names
        if isinstance(fieldlist, str):
            fieldlist = [fieldlist]
        for fld in fieldlist:
            if fld in cls._meta.get_fields():
                fld = fld.name
                
        for fld in fieldlist:
            # Try for an exact match:
            if fld in search_fields:
                rslt.append(search_fields[search_fields.index(fld)])
            # Lastly, try to find parts of it in search_fields:
            elif any(s.find(fld)!=-1 for s in search_fields):
                rslt += [s for s in search_fields if s.find(fld)!=-1]
        return rslt
        
    @classmethod
    def merge(cls, original_pk, dupes, verbose=True):
        return merge_util(cls, original_pk, dupes, verbose)
                
    def merge_with(self, other_record):
        if isinstance(other_record, str):
            try:
                other_record_pk = int(other_record)
            except:
                raise("Failed to obtain other_record_pk. Unable to cast into INT.")
                return
        elif isinstance(other_record, int):
            other_record_pk = other_record
        else:
            try:
                other_record_pk = other_record.pk
            except:
                raise("Failed to obtain other_record_pk. other_record was not a model instance.")
                return
        self.merge([self.pk, other_record_pk])
        
    
        
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
        
class alias_base(ShowModel):
    alias = models.CharField('Alias', max_length = 100,  default = None)
    parent = None
    class Meta:
        verbose_name = 'Alias'
        verbose_name = 'Alias'
        abstract = True

# app models

class person(ShowModel):
    vorname = models.CharField(**CF_ARGS_B)
    nachname = models.CharField(default = 'unbekannt', **CF_ARGS)
    herkunft = models.ForeignKey('ort', null = True,  blank = True,  on_delete=models.PROTECT)
    beschreibung = models.TextField(blank = True)
    
    exclude = [beschreibung]
    
    class Meta:
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

    
class musiker(ShowModel): 
    kuenstler_name = models.CharField('Künstlername', **CF_ARGS)
    person = models.ForeignKey(person, null = True, blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_musiker_genre)
    instrument = models.ManyToManyField('instrument',  through = m2m_musiker_instrument)
    beschreibung = models.TextField(blank = True)
    
    exclude = [beschreibung]
    dupe_fields = ['kuenstler_name', 'person']
    primary_fields = ['kuenstler_name', 'person__vorname', 'person__nachname', 'musiker_alias__alias']
    
    class Meta:
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
    
    
class genre(ShowModel):
    genre = models.CharField('Genre', max_length = 100,   unique = True)
    ober = models.ForeignKey('self', related_name = 'obergenre', verbose_name = 'Oberbegriff', null = True,  blank = True,  on_delete=models.SET_NULL)
    class Meta:
        verbose_name = 'Genre'
        verbose_name_plural = 'Genres'
        ordering = ['genre']
        
    def alias_string(self):
        return concat_limit(self.genre_alias_set.all())
    alias_string.short_description = 'Aliase'
class genre_alias(alias_base):
    parent = models.ForeignKey('genre')
        
        
class band(ShowModel):
    band_name = models.CharField('Bandname', **CF_ARGS)
    herkunft = models.ForeignKey('ort', models.PROTECT, null = True,  blank = True)
    genre = models.ManyToManyField('genre',  through = m2m_band_genre)
    musiker = models.ManyToManyField('musiker',  through = m2m_band_musiker)
    beschreibung = models.TextField(blank = True)
    
    exclude = [beschreibung]
    dupe_fields = ['band_name', 'herkunft_id']
#    search_fields = ['band_name', 'herkunft__stadt', 'herkunft__land__land_name',
#                    'band_alias__alias', 'genre__genre', 'musiker__kuenstler_name']

    
    class Meta:
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
    
    
class autor(ShowModel):
    kuerzel = models.CharField('Kürzel', **CF_ARGS_B)
    person = models.ForeignKey('person', on_delete=models.PROTECT)
    magazin = models.ManyToManyField('magazin', blank = True,  through = m2m_autor_magazin)
    
    primary_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    dupe_fields = ['person__vorname', 'person__nachname', 'kuerzel']
    
    class Meta:
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
    e_datum = models.DateField('Erschienen am', null = True,  blank = True)
    jahrgang = models.PositiveSmallIntegerField(null = True,  blank = True, verbose_name = "Jahrgang")
    info = models.TextField(max_length = 200, blank = True)
    sonderausgabe = models.BooleanField(default=False, verbose_name='Sonderausgabe')
    
    exclude = [info]
    dupe_fields = ['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum',
                    'ausgabe_monat__monat', 'e_datum', 'magazin', 'sonderausgabe']
                    
    primary_fields = ['ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_jahr__jahr', 
                    'ausgabe_monat__monat__monat', 'e_datum']
    
    objects = AusgabeQuerySet.as_manager()
    class Meta:
        verbose_name = 'Ausgabe'
        verbose_name_plural = 'Ausgaben'
        ordering = ['magazin', 'jahrgang']
        
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
        if self.e_datum:
            if self.e_datum.year not in self.ausgabe_jahr_set.values_list('jahr', flat=True):
                self.ausgabe_jahr_set.create(jahr=self.e_datum.year)
            if self.e_datum.month not in self.ausgabe_monat_set.values_list('monat_id', flat=True):
                #NOTE: this actually raised an IntegrityError (UNIQUE Constraints)
                # self.ausgabe_monat_set will be empty but creating a new set instance will still fail
                # need to find out how to reliably reproduce this
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
        try:
            jahre, details = (search_term.split("-"))
        except:
            return None
        jahre_prefix = jahre[:2]
        ajahre = []
        for j in jahre.split("/"):
            if len(j)<4:
                if j=='00':
                    j = '2000'
                else:
                    j = jahre_prefix+j
            ajahre.append(j)
        details = [d for d in details.split("/")]
        
        rslt = [ [models.Q( (prefix+'ausgabe_jahr__jahr__iexact', j))]  for j in ajahre ]
        for d in details:
            qobject = models.Q()
            if d.isnumeric():
                for fld in ['ausgabe_num__num', 'ausgabe_lnum__lnum']:
                    qobject |= models.Q( (prefix+fld, d) )
            else:
                for fld in ['ausgabe_monat__monat__monat', 'ausgabe_monat__monat__abk']:
                    qobject |= models.Q( (prefix+fld, d) )
            rslt.append([qobject])
        return rslt
        
class ausgabe_jahr(ShowModel):
    JAHR_VALIDATORS = [MaxValueValidator(MAX_JAHR),MinValueValidator(MIN_JAHR)]
    
    jahr = models.PositiveSmallIntegerField('Jahr', validators = JAHR_VALIDATORS, default = CUR_JAHR)
    ausgabe = models.ForeignKey('ausgabe')
    class Meta:
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        unique_together = ('jahr', 'ausgabe')
        ordering = ['jahr']
        
class ausgabe_num(ShowModel):
    num = models.IntegerField('Nummer', default = None)
    ausgabe = models.ForeignKey('ausgabe')
    class Meta:
        verbose_name = 'Nummer'
        verbose_name_plural = 'Ausgabennummer'
        unique_together = ('num', 'ausgabe')
        ordering = ['num']
        
class ausgabe_lnum(ShowModel):
    lnum = models.IntegerField('Lfd. Nummer', default = None)
    ausgabe = models.ForeignKey('ausgabe')
    class Meta:
        verbose_name = 'lfd. Nummer'
        verbose_name_plural = 'Laufende Nummer'
        unique_together = ('lnum', 'ausgabe')
        ordering = ['lnum']
        
class ausgabe_monat(ShowModel):
    ausgabe = models.ForeignKey('ausgabe')
    monat = models.ForeignKey('monat')
    class Meta:
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        unique_together = ('ausgabe', 'monat')
        ordering = ['monat']
        
    primary_fields = ['monat__monat', 'monat__abk']
    
    
class monat(ShowModel):
    monat = models.CharField('Monat', **CF_ARGS)
    abk = models.CharField('Abk',  **CF_ARGS)
    class Meta:
        verbose_name = 'Monat'
        verbose_name_plural = 'Monate'
        ordering = ['id']
        
        
class magazin(ShowModel):
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
    
    exclude = [ausgaben_merkmal, info, magazin_url, turnus, erstausgabe]
    primary_fields = [magazin_name]
    
    def anz_ausgaben(self):
        return self.ausgabe_set.count()
    anz_ausgaben.short_description = 'Anz. Ausgaben'
    
    class Meta:
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
            
        
class status(ShowModel):
    STATUS_CHOICES = [('unb','unbearbeitet'), ('iB','in Bearbeitung'), ('abg','abgeschlossen')]
    status = models.CharField('Bearbeitungsstatus', **CF_ARGS)
    class Meta:
        ordering = None
    
    
class turnus(ShowModel):
    TURNUS_CHOICES = [('u', 'unbekannt'), 
        ('t','täglich'), ('w','wöchentlich'), ('2w','zwei-wöchentlich'), ('m','monatlich'), ('2m','zwei-monatlich'), 
        ('q','quartalsweise'), ('hj','halbjährlich'), ('j','jährlich')]
    turnus = models.CharField('Turnus', **CF_ARGS)
    class Meta:
        ordering = None
    
    
class verlag(ShowModel):
    verlag_name = models.CharField('verlag', **CF_ARGS)
    sitz = models.ForeignKey('ort',  null = True,  blank = True, on_delete = models.SET_NULL)
    class Meta:
        verbose_name = 'Verlag'
        verbose_name_plural = 'Verlage'
        ordering = ['verlag_name', 'sitz']


class ort(ShowModel):
    stadt = models.CharField(**CF_ARGS_B)
    bland = models.ForeignKey('bundesland', verbose_name = 'Bundesland',  null = True,  blank = True, on_delete = models.PROTECT)
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
    primary_fields = ['stadt', 'land__land_name', 'bland__bland_name', 'land__code', 'bland__code']
    
    class Meta:
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
            
        
class bundesland(ShowModel):
    bland_name = models.CharField('Bundesland', **CF_ARGS)
    code = models.CharField(max_length = 4,  unique = False)
    land = models.ForeignKey('land', verbose_name = 'Land', on_delete = models.PROTECT)
    
    primary_fields = ['bland_name', 'code']
    
    class Meta:
        verbose_name = 'Bundesland'
        verbose_name_plural = 'Bundesländer'
        unique_together = ('bland_name', 'land')
        ordering = ['land', 'bland_name']                
        
        
class land(ShowModel):
    land_name = models.CharField('Land', max_length = 100,  unique = True)
    code = models.CharField(max_length = 4,  unique = True)
    
    primary_fields = ['land_name', 'code']
    
    class Meta:
        verbose_name = 'Land'
        verbose_name_plural = 'Länder'
        ordering = ['land_name']
class land_alias(alias_base):
    parent = models.ForeignKey('land')

        
class schlagwort(ShowModel):
    schlagwort = models.CharField( max_length = 100,  unique = True)
    ober = models.ForeignKey('self', related_name = 'oberschl', verbose_name = 'Oberbegriff', null = True,  blank = True)
    
    class Meta:
        verbose_name = 'Schlagwort'
        verbose_name_plural = 'Schlagwörter'
        ordering = ['schlagwort']
class schlagwort_alias(alias_base):
    parent = models.ForeignKey('schlagwort')
        
        
class artikel(ShowModel):
    F = 'f'
    FF = 'ff'
    SU_CHOICES = [(F, 'f'), (FF, 'ff')]
    
    ausgabe = models.ForeignKey('ausgabe',  on_delete=models.PROTECT)
    schlagzeile = models.CharField(**CF_ARGS)
    seite = models.IntegerField(verbose_name="Seite") #TODO: PositiveSmallIntegerField
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
    primary_fields = ['schlagzeile']
    
    search_fields = {'schlagzeile', 'zusammenfassung', 'seite', 'seitenumfang', 'info'}

    
    class Meta:
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
    
    def artikel_magazin(self):
        return self.ausgabe.magazin
    artikel_magazin.short_description = 'Magazin'
    
    def schlagwort_string(self):
        return concat_limit(self.schlagwort.all())
    schlagwort_string.short_description = 'Schlagwörter'
    
    def kuenstler_string(self):
        return concat_limit(list(self.band.all()) + list(self.musiker.all()))
    kuenstler_string.short_description = 'Künstler'
        

class buch(ShowModel):
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
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Buch'
        verbose_name_plural = 'Bücher'
        
    def __str__(self):
        return str(self.titel)
    

class instrument(ShowModel):
    instrument = models.CharField(unique = True, **CF_ARGS)
    kuerzel = models.CharField(**CF_ARGS_B)
    
    primary_fields = ['instrument', 'kuerzel']
    
    class Meta:
        verbose_name = 'Instrument'
        verbose_name_plural = 'Instrumente'
class instrument_alias(alias_base):
    parent = models.ForeignKey('instrument')
        
        
class audio(ShowModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()
    laufzeit = models.DurationField()
    festplatte = models.CharField(**CF_ARGS_B)
    quelle = models.CharField(**CF_ARGS_B)
    sender = models.ForeignKey('sender',  blank = True,  null = True)
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Audio Material'
        verbose_name_plural = 'Audio Materialien'
        
    def __str__(self):
        return str(self.titel)
    
    
class bildmaterial(ShowModel):
    titel = models.CharField(**CF_ARGS)
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Bild Material'
        verbose_name_plural = 'Bild Materialien'
        
        
class buch_serie(ShowModel):
    serie = models.CharField(**CF_ARGS)
    
    primary_fields = ['serie']
    
    class Meta:
        verbose_name = 'Buchserie'
        verbose_name_plural = 'Buchserien'
        
        
class dokument(ShowModel):
    titel = models.CharField(**CF_ARGS)
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Dokument'
        verbose_name_plural = 'Dokumente'
    
    
class kreis(ShowModel):
    name = models.CharField(**CF_ARGS)
    bland = models.ForeignKey('bundesland')
    
    class Meta:
        verbose_name = 'Kreis'
        verbose_name_plural = 'Kreise'
        
        
class memorabilien(ShowModel):
    titel = models.CharField(**CF_ARGS)
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Memorabilia'
        verbose_name_plural = 'Memorabilien'
        ordering = ['titel']
        
        
class sender(ShowModel):
    name = models.CharField(**CF_ARGS)
    
    class Meta:
        verbose_name = 'Sender'
        verbose_name_plural = 'Sender'
        ordering = ['name']
class sender_alias(alias_base):
    parent = models.ForeignKey('sender')
    
    
class spielort(ShowModel):
    name = models.CharField(**CF_ARGS)
    ort = models.ForeignKey('ort')
    
    primary_fields = ['name']
    
    class Meta:
        verbose_name = 'Spielort'
        verbose_name_plural = 'Spielorte'
        ordering = ['name']
class spielort_alias(alias_base):
    parent = models.ForeignKey('spielort')
    
    
class sprache(ShowModel):
    sprache = models.CharField(**CF_ARGS)
    abk = models.CharField(max_length = 3)
    
    class Meta:
        verbose_name = 'Sprache'
        verbose_name_plural = 'Sprachen'
        ordering = ['sprache']
    
class technik(ShowModel):
    titel = models.CharField(**CF_ARGS)
    
    primary_fields = ['name']
    
    class Meta:
        verbose_name = 'Technik'
        verbose_name_plural = 'Technik'
        ordering = ['titel']
        
    
class veranstaltung(ShowModel):
    name = models.CharField(**CF_ARGS)
    datum = models.DateField()
    spielort = models.ForeignKey('spielort')
    ort = models.ForeignKey('ort',  null = True,  blank = True)
    
    genre = models.ManyToManyField('genre',  through = m2m_veranstaltung_genre)
    person = models.ManyToManyField('person', verbose_name = 'Teilnehmer (Personen)', through = m2m_veranstaltung_person)
    band = models.ManyToManyField('band', verbose_name = 'Teilnehmer (Bands)',  through = m2m_veranstaltung_band)
    #NYI: musiker = models.ManyToManyField('musiker', through = m2m_veranstaltung_musiker)#
    
    primary_fields = ['name']
    
    class Meta:
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'
        ordering = ['name', 'spielort', 'ort', 'datum']
class veranstaltung_alias(alias_base):
    parent = models.ForeignKey('veranstaltung')


class video(ShowModel):
    titel = models.CharField(**CF_ARGS)
    tracks = models.IntegerField()
    laufzeit = models.TimeField()
    festplatte = models.CharField(**CF_ARGS_B)
    quelle = models.CharField(**CF_ARGS_B)
    sender = models.ForeignKey('sender')
    
    primary_fields = ['titel']
    
    class Meta:
        verbose_name = 'Video Material'
        verbose_name_plural = 'Video Materialien'
        ordering = ['titel']
        
    
class provenienz(ShowModel):
    SCHENK = 'Schenkung'
    SPENDE = 'Spende'
    FUND = 'Fund'
    LEIHG = 'Leihgabe'
    DAUERLEIHG = 'Dauerleihgabe'
    TYP_CHOICES = [(SCHENK, 'Schenkung'), (SPENDE, 'Spende'), (FUND,'Fund'), (LEIHG, 'Leihgabe'), (DAUERLEIHG,'Dauerleihgabe')]
    geber = models.ForeignKey('geber')
    typ = models.CharField('Art der Provenienz',  max_length = 100,  choices = TYP_CHOICES,  default = TYP_CHOICES[0][0])
    
    primary_fields = ['geber__name']
    
    class Meta:
        verbose_name = 'Provenienz'
        verbose_name_plural = 'Provenienzen'
        
    def __str__(self):
        return "{0} ({1})".format(str(self.geber.name), str(self.typ))
class geber(ShowModel):
    name = models.CharField(default = 'unbekannt', **CF_ARGS)
        
        
class lagerort(ShowModel):
    ort = models.CharField(**CF_ARGS)
    raum = models.CharField(**CF_ARGS_B)
    regal = models.CharField(**CF_ARGS_B)
    
    signatur = models.CharField(**CF_ARGS_B) # NOTE: use? maybe for human-readable shorthand?
    class Meta:
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
        
        
class bestand(ShowModel):
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
    
    
    class Meta:
        verbose_name = 'Bestand'
        verbose_name_plural = 'Bestände'

    def __str__(self):
        return str(self.lagerort)

# Testmagazin for... testing
tmag = magazin.objects.get(pk=326)
