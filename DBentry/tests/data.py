import random

from django.db.models import fields
from django.db import transaction
from django.db.models.deletion import ProtectedError

from DBentry.models import *

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
    
    obj2 = ausgabe(magazin=tmag, info='Testmerge')
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
    exclude = [Favoriten]

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
    
    def get_value(self, fld):
        value = None
        t = fld.get_internal_type()
        if t in ('CharField', 'TextField'):
            value = 'Test-{}'.format(random.randrange(100))
        elif t in ('NullBooleanField', 'BooleanField'):
            value = random.choice([True, False])
        elif t in ('PositiveSmallIntegerField', 'SmallIntegerField', 'IntegerField', 'BigIntegerField', 'DurationField'):
            value = random.randrange(100)
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

    
    _created = []
        
    def create_obj(self, model, create_new = False):
        #TODO: a cached instance of a model object may point to  an already deleted DB object
        #TODO: this doesn't respect field limitations like max_length!!
        attr_name = '_' + model._meta.model_name
        obj = getattr(self, attr_name, None)
#        if not create_new and not obj is None and obj.pk or :
#            return obj
        if create_new or obj is None or obj.pk is None:
            if not hasattr(model, 'get_required_fields'):
                # Auto-created through table (e.g. Favoriten)
                return None
            obj_dict = {}
            for fld in model.get_required_fields():
                if fld.is_relation:
                    rel_attr_name = '_' + fld.related_model._meta.model_name
                    req_obj = getattr(self, rel_attr_name, None)
                    if req_obj is None or req_obj.pk is None:
                        req_obj = self.create_obj(fld.related_model)
                else:
                    req_obj = self.get_value(fld)
#                    if fld.has_default() and fld.get_default() is not None:
#                        req_obj = fld.get_default()
#                    elif fld.get_internal_type() in self.defaults:
#                        req_obj = self.defaults[fld.get_internal_type()]
#                    else:
#                        raise Exception("WARNING: no default for field-type:", fld.get_internal_type())
                obj_dict[fld.name] = req_obj
            try:
                with transaction.atomic():
                    obj = model.objects.create(**obj_dict)
            except IntegrityError:
                # Tried to create a duplicate of an unique object
                # TODO: add a random bit to obj_dict to make it unique
                    with transaction.atomic():
                        obj = model.objects.get(**obj_dict)
            self._created.append(obj)
            setattr(self, attr_name, obj)
        return obj
        
    def add_relations(self, instance_list):
        if instance_list:
            for rel in instance_list[-1]._meta.related_objects:
                if rel.many_to_many:
                    related_model = rel.through
                else:
                    related_model = rel.field.model
                if related_model in self.exclude:
                    continue
                for instance in instance_list:
                    setattr(self, '_' + instance._meta.model_name, instance) # Set cached instance to the instance we are currently working on to assign relations to it
                    self.create_obj(related_model, create_new = True)
        
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
            
