from collections import OrderedDict
from nameparser import HumanName

from DBentry.models import autor, person
from DBentry.utils import parse_name


class MultipleObjectsReturnedException(Exception):
    message = 'Name nicht einzigartig.'


class FailedObject(object):
    """
    A dummy object that immitates a result object should creation fail.

    dal views expect _some_ object with a pk attribute and string representation
    further down the chain (get_result_label, etc.).
    When the saving of a new (unique) model instance fails due to a
    MultipleObjectsReturned exception, and when that exception is not allowed
    to bubble up, a FailedObject will be created instead.
    """

    def __init__(self, text):
        self.pk = 0
        self.text = text

    def __str__(self):
        return self.text


class Creator(object):
    """
    Create a model instance from a text input.

    A helper class that uses a declared 'create_<model_name>' method to create
    a model instance from a given string.
    """

    def __init__(self, model, raise_exceptions=False):
        self.model = model
        self.raise_exceptions = raise_exceptions
        self.creator = getattr(self, 'create_' + model._meta.model_name, None)

    def create(self, text, preview=True):
        """
        Try to create a model instance from the string 'text'.

        If preview is True, no new database records will be created.
        """
        if self.creator is None:
            return {}

        try:
            return self.creator(text, preview)
        except MultipleObjectsReturnedException as e:
            if self.raise_exceptions:
                raise e
            if preview:
                return {}
            # The dal view's post response expects an object with pk and
            # text attribute (which FailedObject emulates).
            return {'instance': FailedObject(str(e))}

    def _get_model_instance(self, model, **data):
        """
        Using get(), query for an existing model instance with 'data'.

        If the query returns exactly one instance, return that instance.
        If the query returned no results, return a new unsaved instance.
        Otherwise raise a MultipleObjectsReturned exception.
        """
        try:
            return model.objects.get(**data)
        except model.DoesNotExist:
            return model(**data)
        except model.MultipleObjectsReturned:
            raise MultipleObjectsReturnedException

    def create_person(self, text, preview=True):
        """
        Get or create a person instance from `text`.

        If preview is True, do not save the found instance even if it is new.

        Return an OrderedDict that includes the instance and additional
        information for the 'create_option' of a dal widget.
        """
        # parse_name will join first and middle names
        vorname, nachname = parse_name(text)
        person_instance = self._get_model_instance(
            person, vorname=vorname, nachname=nachname
        )
        if not preview and person_instance.pk is None:
            person_instance.save()
        return OrderedDict([
            ('Vorname', vorname), ('Nachname', nachname),
            ('instance', person_instance)
        ])

    def create_autor(self, text, preview=True):
        """
        Get or create an autor instance from `text`.

        If preview is True, do not save the found instance even if it is new.

        Return an OrderedDict that includes the instance and additional
        information for the 'create_option' of a dal widget.
        """
        name = HumanName(text)
        kuerzel = name.nickname
        name.nickname = ''
        p = self.create_person(name, preview)
        person_instance = p.get('instance')
        autor_instance = self._get_model_instance(
            autor, person=person_instance, kuerzel=kuerzel
        )
        if not preview and autor_instance.pk is None:
            if autor_instance.person.pk is None:
                autor_instance.person.save()
            autor_instance.save()
        return OrderedDict([
            ('Person', p), ('Kürzel', kuerzel), ('instance', autor_instance)
        ])
