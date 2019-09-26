from collections import OrderedDict

from nameparser import HumanName

from DBentry.models import autor, person
from DBentry.utils import parse_name


class MultipleObjectsReturnedException(Exception):
    message = 'Name nicht einzigartig.'


class FailedObject(object):
    """An object that immitates an object that is expected by the dal view."""

    def __init__(self, text):
        self.pk = 0
        self.text = text

    def __str__(self):
        return self.text


class Creator(object):
    """A helper class that uses a declared `create_<model_name>` method to
    create a model instance from a given string.
    """

    def __init__(self, model, raise_exceptions=False):
        self.model = model
        self.raise_exceptions = raise_exceptions
        self.creator = getattr(self, 'create_' + model._meta.model_name, None)

    def create(self, text, preview=True):
        if self.creator is None:
            return {}

        try:
            created = self.creator(text, preview)
        except MultipleObjectsReturnedException as e:
            if self.raise_exceptions:
                raise e
            if preview:
                return {}
            # the dal view's post response expects an object with pk and
            # text attribute (which FailedObject emulates).
            return {'instance': FailedObject(str(e))}
        else:
            return created

    def _get_model_instance(self, model, **data):
        """
        Query for an existing model instance with `data` and return:
             - a new unsaved instance if the query did not find anything
             - the singular model instance found by the query
        or raise a MultipleObjectsReturnedException to signal that filtering
        with `data` returned more than one result.
        """
        possible_instances = list(model.objects.filter(**data))
        if len(possible_instances) == 0:
            return model(**data)
        elif len(possible_instances) == 1:
            return possible_instances[0]
        else:
            raise MultipleObjectsReturnedException

    def create_person(self, text, preview=True):
        """Create a person instance from `text`.

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
        """Create an autor instance from `text`.

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
