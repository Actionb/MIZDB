from collections import OrderedDict

from DBentry.models import *

# isn't this very close to validation of form fields?
#TODO: store created object/create_info etc.
#TODO: allow or disallow 'duplicating' records?
#TODO: create, createable and create_info all do the same thing
    
class FormatException(Exception):
    message = 'Formatierung fehlgeschlagen.'
    
class MultipleObjectsReturnedException(Exception):
    message = 'Name nicht einzigartig.'
    

def split_name(full_name):
    #TODO: move to utils.py
    try:
        if ',' in full_name:
            nachname, vorname = full_name.strip().split(',')
        else:
            vorname, nachname = full_name.strip().rsplit(' ', 1)
    except ValueError:
        raise FormatException()
    return vorname.strip(), nachname.strip()
        
def _format_name(full_name):
    vorname, nachname = split_name(full_name.strip())
    if vorname and not nachname:
        raise FormatException('Kein Nachname.')
    return vorname, nachname
    
class FailedObject(object):
    """
    An object that immitates an object that is expected by the dal view.
    """
    
    def __init__(self, text):
        self.pk = 0
        self.text = text
        
    def __str__(self):
        return self.text
        
class Creator(object):
    
    def __init__(self, model, raise_exceptions = False):
        self.model = model
        self.creator = getattr(self, 'create_' + model._meta.model_name, lambda text, dry_run: None)
        self.raise_exceptions = raise_exceptions
    
    def create(self, text):
        try:
            created = self.creator(text, False)
        except (FormatException, MultipleObjectsReturnedException) as e:
            if self.raise_exceptions:
                raise e
            created = FailedObject(e.message)
        return created
    
    def createable(self, text):
        try:
            createable = self.creator(text, True) or False
        except Exception as e:
            if self.raise_exceptions:
                raise e
            return False
        if isinstance(createable, OrderedDict) and 'instance' in createable:
            # Return False if a record that fits 'text' already exists
            return createable.get('instance').pk is None
        return bool(createable)
        
    def create_info(self, text):
        create_info = OrderedDict()
        try:
            create_info = self.creator(text, True)
        except Exception as e:
            if self.raise_exceptions:
                raise e
        return create_info
    
    def _get_model_instance(self, model, **data):
        possible_instances = list(model.objects.filter(**data))
        if len(possible_instances) == 0:
            return model(**data)
        elif len(possible_instances) == 1:
            return possible_instances[0]
        else:
            raise MultipleObjectsReturnedException
        
        
    def create_person(self, text, dry_run = False):
        vorname, nachname = _format_name(text.strip())
        
        p = self._get_model_instance(person, vorname = vorname, nachname = nachname)
        
        if not dry_run and p.pk is None:
            p.save()
        return OrderedDict([('Vorname', p.vorname), ('Nachname', p.nachname), ('instance', p)])    
        
    def create_autor(self, text, dry_run = False):
        # format: 'full_name (kuerzel)' -> full_name: (vorname nachname or nachname, vorname)
        name, _, kuerzel = text.strip().partition('(')
        kuerzel = kuerzel.replace(')', '')
            
        p = self.create_person(name, dry_run)
        person_instance = p.get('instance')
        
        if person_instance.pk is None:
            # the person is new, there cannot be any autor records with it
            autor_instance = autor(person = person_instance, kuerzel = kuerzel)
        else:
            autor_instance = self._get_model_instance(autor, person = person_instance, kuerzel = kuerzel)
            
        if not dry_run and autor_instance.pk is None:
            if autor_instance.person.pk is None:
                autor_instance.person.save()
            autor_instance.save()
        return OrderedDict([('Person', p), ('Kürzel', kuerzel), ('instance', autor_instance)]) 
