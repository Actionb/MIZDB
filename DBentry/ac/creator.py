from collections import OrderedDict

from nameparser import HumanName

from DBentry.models import autor, person
from DBentry.utils import parse_name

#TODO: Surname, Firstname does not seem to be recognized anymore!
    
class MultipleObjectsReturnedException(Exception):
    message = 'Name nicht einzigartig.'
    
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
    """
    A helper class that uses a declared `create_<model_name>` method to create a model instance from a given string.
    """
    
    def __init__(self, model, raise_exceptions = False):
        self.model = model
        self.raise_exceptions = raise_exceptions
        self.creator = getattr(self, 'create_' + model._meta.model_name, None)
        
    def create(self, text, preview = True):
        if self.creator is None:
            return {}
            
        try:
            created = self.creator(text, preview)
        except MultipleObjectsReturnedException as e:
            if self.raise_exceptions:
                raise e
            if preview:
                return {}
            # the dal view's post response expects an object with pk and text attribute 
            return {'instance': FailedObject(e.message)}
        else:
            return created
        
    def _get_model_instance(self, model, **data):
        """
        Queries for an existing model instance with `data` and returns:
             - a new instance if the query did not find anything
             - the singular model instance found by the query 
        or raises a MultipleObjectsReturnedException to signal that a full instance cannot be created with `data`.
        """
        possible_instances = list(model.objects.filter(**data))
        if len(possible_instances) == 0:
            return model(**data)
        elif len(possible_instances) == 1:
            return possible_instances[0]
        else:
            raise MultipleObjectsReturnedException
            
    def create_person(self, text, preview = True):
        vorname, nachname = parse_name(text)

        person_instance = self._get_model_instance(person, vorname = vorname, nachname = nachname)
        if not preview and person_instance.pk is None:
            person_instance.save()
        
        return OrderedDict([('Vorname', vorname), ('Nachname', nachname), ('instance', person_instance)])    
        
    def create_autor(self, text, preview = True):
        name = HumanName(text)
        kuerzel = name.nickname
        name.nickname = ''
            
        p = self.create_person(name, preview)
        
        person_instance = p.get('instance')
        autor_instance = self._get_model_instance(autor, person = person_instance, kuerzel = kuerzel)
            
        if not preview and autor_instance.pk is None:
            if autor_instance.person.pk is None:
                autor_instance.person.save()
            autor_instance.save()
        return OrderedDict([('Person', p), ('Kürzel', kuerzel), ('instance', autor_instance)]) 
