import random

from django.db.models import fields
from django.db import transaction
from django.db.models.deletion import ProtectedError

from DBentry.models import *

class DataFactory(object):
# Available internal types : db types
#{
#'GenericIPAddressField': 'char(39)', 
#'NullBooleanField': 'bool', 
#'FloatField': 'real', 
#'BinaryField': 'BLOB', 
#'PositiveSmallIntegerField': 'smallint unsigned', 
#'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
#'DateField': 'date', 
#'IntegerField': 'integer', 
#'UUIDField': 'char(32)', 
#'BigAutoField': 'integer', 
#'BooleanField': 'bool', 
#'DurationField': 'bigint', 
#'FilePathField': 'varchar(%(max_length)s)', 
#'IPAddressField': 'char(15)', 
#'PositiveIntegerField': 'integer unsigned', 
#'AutoField': 'integer', 
#'CharField': 'varchar(%(max_length)s)', 
#'TimeField': 'time', 
#'SmallIntegerField': 'smallint', 
#'SlugField': 'varchar(%(max_length)s)', 
#'OneToOneField': 'integer', 
#'TextField': 'text', 
#'FileField': 'varchar(%(max_length)s)', 
#'BigIntegerField': 'bigint', 
#'DecimalField': 'decimal', 
#'DateTimeField': 'datetime'
#}
    exclude = [Favoriten.fav_genres.through, Favoriten.fav_schl.through]

    defaults = {
        'CharField' : 'Test', 
        'TextField' : 'Test', 
        'NullBooleanField' : False, 
        'BooleanField' : False, 
        'PositiveSmallIntegerField' : 20, 
        'DateField' : '2010-01-01', 
        'DurationField' : 2000, 
        'SmallIntegerField' : 20, 
        'BigIntegerField' : 2020, 
        'DateTimeField' : '2010-01-01', 
        'IntegerField' : 20, 
        'TimeField' : '20:20', 
        
    }
    
    _created = []
    
    def get_value(self, fld):
        value = None
        t = fld.get_internal_type()
        if t in ('CharField', 'TextField'):
            value = 'Test-{}'.format(random.randrange(10000))
        elif t in ('NullBooleanField', 'BooleanField'):
            value = random.choice([True, False])
        elif t in ('PositiveSmallIntegerField', 'SmallIntegerField', 'IntegerField', 'BigIntegerField', 'DurationField'):
            value = random.randrange(1000)
        elif t in ('DateField', 'DateTimeField'):
            value = "{y}-{m}-{d}".format(
                y  = random.randrange(1900, 2017), 
                m = random.randrange(1, 12), 
                d = random.randrange(1, 28))
        elif t in ('TimeField'):
            value = "{h}:{m}".format(h = random.randrange(1, 23), m = random.randrange(1, 59))
        else:
            raise Exception("WARNING: no default for field-type:", fld.get_internal_type())
        return value
    
    def get_obj_dict(self, model):
        obj_dict = {}
        if model._meta.auto_created:
            required_fields = [f for f in model._meta.get_fields() if f.is_relation]
        else:
            required_fields = model.get_required_fields()
        for fld in required_fields:
            if fld.is_relation:
                if fld.related_model == model:
                    # a self relation
                    req_obj = self.create_obj(fld.related_model, add_to_cache = False)
                else:
                    rel_attr_name = '_' + fld.related_model._meta.model_name
                    req_obj = getattr(self, rel_attr_name, None)
                    if req_obj is None or req_obj.pk is None:
                        req_obj = self.create_obj(fld.related_model)
            else:
                req_obj = self.get_value(fld)
            obj_dict[fld.name] = req_obj
        return obj_dict
        
    def create_obj(self, model, create_new = False, add_to_cache = True):
        #TODO: a cached instance of a model object may point to  an already deleted DB object
        #TODO: this doesn't respect field limitations like max_length!!
        attr_name = '_' + model._meta.model_name
        obj = getattr(self, attr_name, None)
#        if not create_new and not obj is None and obj.pk or :
#            return obj
        if create_new or obj is None or obj.pk is None:
#            if not hasattr(model, 'get_required_fields'):
#                # Auto-created through table (e.g. Favoriten)
#                return None
            sanity = 10
            while(sanity):
                obj_dict = self.get_obj_dict(model)
                try:
                    with transaction.atomic():
                        obj = model.objects.create(**obj_dict)
                except IntegrityError:
                    # Tried to create a duplicate of an unique object, try again with a new obj_dict
                    sanity -=1
                    continue
                else:
                    break
            self._created.append(obj)
            if add_to_cache:
                setattr(self, attr_name, obj)
        return obj
        
    def add_relations(self, instance_list):
        if instance_list:
            model = instance_list[0]._meta.model
            for rel in get_model_relations(model, forward = False):
                if rel.many_to_many:
                    related_model = rel.through
#                elif rel.concrete:
#                    if rel.related_model == model:
#                        # a self relation
#                        req_obj = self.create_obj(model, add_to_cache = False)
#                    else:
#                        # a concrete ForeignKey field, get_obj_dict() will have dealt with those
#                        continue
                else:
                    # a reverse ForeignKey/ManyToOneRel
                    related_model = rel.related_model
                if related_model in self.exclude:
                    continue
                for instance in instance_list:
                    setattr(self, '_' + instance._meta.model_name, instance) # Set cached instance to the instance we are currently working on to assign relations to it
                    obj = self.create_obj(related_model, create_new = True, add_to_cache = related_model != model)
                    if related_model == model:
                        getattr(instance, rel.get_accessor_name()).add(obj)
        
    def create_data(self, model, count=3, add_relations = True):
        instance_list = []
        for c in range(count):
            obj = self.create_obj(model, create_new = True)
            instance_list.append(obj)
        if add_relations:
            self.add_relations(instance_list)
        return instance_list
        
    def delete_object(self, obj):
        if obj and obj.pk:
            attr_name = '_'+ obj._meta.model_name
            try:
                obj.delete()
            except ProtectedError as e:
                for protected_obj in e.protected_objects:
                    self.delete_object(protected_obj)
            try:
                delattr(self, attr_name)
            except AttributeError:
                pass
        
    def destroy(self):
        while True:
            if len(self._created) == 0:
                break
            obj = self._created.pop()
            self.delete_object(obj)

def ausgabe_data_simple(cls):
    cls.model = ausgabe
    cls.mag = magazin.objects.create(magazin_name='Testmagazin')
    cls.obj1 = cls.model.objects.create(magazin=cls.mag)
    cls.monat = monat.objects.create(pk=12, monat='Dezember', abk='Dez')
    
    cls.obj2 = cls.model.objects.create(magazin=cls.mag)
    cls.obj2.ausgabe_jahr_set.create(jahr=2000)
    cls.obj2.ausgabe_num_set.create(num=12)
    cls.obj2.ausgabe_lnum_set.create(lnum=12)
    cls.obj2.ausgabe_monat_set.create(monat_id=12)
    
    cls.test_data = [cls.obj1, cls.obj2]
    
def ausgabe_data_str(cls):
    cls.model = ausgabe
    cls.mag = magazin.objects.create(magazin_name='Testmagazin')
    cls.obj1 = ausgabe.objects.create(magazin=cls.mag, beschreibung='Snowflake', sonderausgabe=True)
    
    cls.obj2 = ausgabe.objects.create(magazin=cls.mag, beschreibung='Snowflake', sonderausgabe=False)
    
    cls.obj3 = ausgabe.objects.create(magazin=cls.mag)
    cls.obj3.ausgabe_jahr_set.create(jahr=2000)
    cls.obj3.ausgabe_jahr_set.create(jahr=2001)
    cls.obj3.ausgabe_num_set.create(num=1)
    cls.obj3.ausgabe_num_set.create(num=2)
    
    cls.obj4 = ausgabe.objects.create(magazin=cls.mag)
    cls.obj4.ausgabe_jahr_set.create(jahr=2000)
    cls.obj4.ausgabe_jahr_set.create(jahr=2001)
    cls.obj4.ausgabe_lnum_set.create(lnum=1)
    cls.obj4.ausgabe_lnum_set.create(lnum=2)
    
    cls.obj5 = ausgabe.objects.create(magazin=cls.mag)
    cls.obj5.ausgabe_jahr_set.create(jahr=2000)
    cls.obj5.ausgabe_jahr_set.create(jahr=2001)
    cls.obj5.ausgabe_monat_set.create(monat=monat.objects.create(monat='Januar', abk='Jan'))
    cls.obj5.ausgabe_monat_set.create(monat=monat.objects.create(monat='Februar', abk='Feb'))
    
    cls.obj6 = ausgabe.objects.create(magazin=cls.mag, e_datum='2000-01-01') 
    
    cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4, cls.obj5, cls.obj6]
    
    
def band_data(cls):
    cls.model = band
    cls.obj1 = band.objects.create(band_name='Testband1')
    cls.obj2 = band.objects.create(band_name='Testband2')
    cls.obj3 = band.objects.create(band_name='Testband3')
    
    # m2o
    cls.obj2.band_alias_set.create(alias='Coffee')
    cls.obj3.band_alias_set.create(alias='Juice')
    cls.obj3.band_alias_set.create(alias='Water')
    
    # m2m
    genre1 = genre.objects.create(genre='Rock')
    genre2 = genre.objects.create(genre='Jazz')
    band.genre.through.objects.create(genre=genre1, band=cls.obj2)
    band.genre.through.objects.create(genre=genre1, band=cls.obj3)
    band.genre.through.objects.create(genre=genre2, band=cls.obj3)
    
    cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
    
    

def ausgabe_data():
    model = ausgabe
    instance_list = []
    tmag = magazin.objects.create(magazin_name='Testmagazin')
    lo1 = lagerort.objects.create(ort='TestLagerOrt')
    lo2 = lagerort.objects.create(ort='TestLagerOrt2')
    prov = provenienz.objects.create(geber=geber.objects.create(name='TestCase'))
    
    obj1 = ausgabe(magazin=tmag)
    obj1.save()
    obj1.ausgabe_jahr_set.create(jahr=2000)
    obj1.ausgabe_num_set.create(num=1)
    obj1.bestand_set.create(lagerort=lo1, provenienz = prov)
    instance_list.append(obj1)
    
    obj2 = ausgabe(magazin=tmag, beschreibung='Testmerge')
    obj2.save()
    obj2.ausgabe_jahr_set.create(jahr=2000)
    obj2.ausgabe_num_set.create(num=2)
    obj2.bestand_set.create(lagerort=lo1)
    obj2.bestand_set.create(lagerort=lo2, provenienz = prov)
    instance_list.append(obj2)
    
    obj3 = ausgabe(magazin=tmag)
    obj3.save()
    obj3.ausgabe_jahr_set.create(jahr=2000)
    obj3.ausgabe_num_set.create(num=3)
    obj3.bestand_set.create(lagerort=lo2)
    instance_list.append(obj3)
    
    return model, instance_list
    
def ort_data():
    model = ort
    instance_list = []
    test_magazin = magazin.objects.create(magazin_name='Testmagazin')
    test_ausgabe = ausgabe.objects.create(magazin=test_magazin)
    test_artikel = artikel.objects.create(schlagzeile='MERGE ME',seite=1,ausgabe=test_ausgabe)
    test_land = land.objects.create(land_name='Testland')
    
    obj1 = ort.objects.create(land=test_land, stadt='Stockholm')
    instance_list.append(obj1)
    
    obj2 = ort.objects.create(land=test_land, stadt='Stockholm')
    artikel.ort.through.objects.create(ort=obj2, artikel=test_artikel)
    instance_list.append(obj2)
    
    return model, instance_list
        
        
def band_huge(cls, get_instances=False):
    print("\n Creating test data...", end='')
    cls.model = band
    l = land.objects.create(land_name='Testland')
    objects = [ort(pk=c, stadt='Test-{}'.format(c), land=l) for c in range(1, 5000)]
    ort.objects.bulk_create(objects)
    objects = [genre(pk=c, genre='Test-{}'.format(c)) for c in range(1, 5000)]
    genre.objects.bulk_create(objects)
    
    objects = [band(pk=c, band_name='Test-{}'.format(c), herkunft_id=c) for c in range(1, 5000)]
    band.objects.bulk_create(objects)
    
    objects = [musiker(pk=c, kuenstler_name='Test-{}'.format(c)) for c in range(1, 5000)]
    musiker.objects.bulk_create(objects)
    objects = [m2m_band_musiker(band_id=c, musiker_id=c) for c in range(1, 5000)]
    m2m_band_musiker.objects.bulk_create(objects)
    
    objects = [band_alias(parent_id=c, alias='Test-{}'.format(5000-c)) for c in range(1, 5000)]
    band_alias.objects.bulk_create(objects)
    
    print("...done.")
    if get_instances:
        cls.test_data = [band.objects.get(band_name='Test-{}'.format(c)) for c in range(1, 5000)]
