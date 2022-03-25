from collections import OrderedDict
from typing import Dict, Type, Union

from django.db.models import Model
from nameparser import HumanName

from dbentry import models as _models
from dbentry.utils import parse_name


class MultipleObjectsReturned(Exception):
    """The query returned multiple objects for the given text."""

    message = 'Name nicht einzigartig.'


class FailedObject(object):
    """
    A dummy object that imitates a result object should creation fail.

    dal views expect some object with a pk attribute and string representation
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

    A helper class that uses a declared ``create_<model_name>`` method to
    create a model instance from a given string.
    """

    def __init__(self, model: Type[Model], raise_exceptions: bool = False) -> None:
        """
        Set attributes and assign the creator method.

        Args:
            model (model class): the model class for which instances should be
                created
            raise_exceptions (boolean): if False, suppress MultipleObjectsReturned
              exceptions and return a FailedObject dummy object instead
        """
        self.model = model
        self.raise_exceptions = raise_exceptions
        # noinspection PyUnresolvedReferences
        self.creator = getattr(self, 'create_' + model._meta.model_name, None)

    def create(self, text: str, preview: bool = True) -> Union[Dict, OrderedDict]:
        """
        Try to create a model instance from the string ``text``.

        Args:
            text (str): the text passed to the creator to create the instance
                with
            preview (bool): if True, do not save the created instance

        Returns:
            OrderedDict that includes the created instance and additional
                information for the 'create_option' of a dal widget

        Raises:
            creator.MultipleObjectsReturned: if raise_exceptions is True; the
                creator has found multiple already existing objects that fit
                'text'.
        """
        if self.creator is None:
            return {}

        try:
            return self.creator(text, preview)
        except MultipleObjectsReturned as e:
            if self.raise_exceptions:
                raise e
            if preview:
                return {}
            # The dal view's post response expects an object with pk and
            # text attribute (which FailedObject emulates).
            return {'instance': FailedObject(str(e))}

    def create_person(self, text: Union[str, HumanName], preview: bool = True) -> OrderedDict:
        """
        Get or create a Person instance from the name ``text``.

        If ``preview`` is True, do not save the instance even if it is new.

        Returns:
            OrderedDict that includes the created instance and additional
                information for the 'create_option' of a dal widget

        Raises:
            MultipleObjectsReturned: when the query for that name returned
                multiple matching existing records
        """
        # parse_name will join first and middle names
        vorname, nachname = parse_name(text)
        try:
            p = _models.Person.objects.get(vorname=vorname, nachname=nachname)
        except _models.Person.DoesNotExist:  # noqa
            p = _models.Person(vorname=vorname, nachname=nachname)
        except _models.Person.MultipleObjectsReturned:  # noqa
            raise MultipleObjectsReturned
        if not preview and p.pk is None:
            p.save()
        return OrderedDict(
            [
                ('Vorname', vorname), ('Nachname', nachname),
                ('instance', p)
            ]
        )

    def create_autor(self, text: str, preview: bool = True):
        """
        Get or create an autor instance from name ``text``.

        If ``preview`` is True, do not save the instance even if it is new.

        Returns:
            OrderedDict that includes the created instance and additional
                information for the 'create_option' of a dal widget

        Raises:
            MultipleObjectsReturned: when the query for that name returned
                multiple matching existing records
        """
        # Parse the name through the nameparser to find out the nickname, which
        # will be used as kuerzel. Then pass the name without nickname to the
        # Person constructor.
        name = HumanName(text)
        kuerzel = name.nickname
        name.nickname = ''
        p = self.create_person(str(name), preview)
        person_instance = p['instance']
        try:
            autor_instance = _models.Autor.objects.get(
                kuerzel=kuerzel,
                person__vorname=person_instance.vorname,
                person__nachname=person_instance.nachname
            )
        except _models.Autor.DoesNotExist:  # noqa
            autor_instance = _models.Autor(kuerzel=kuerzel, person=person_instance)
        except _models.Autor.MultipleObjectsReturned:  # noqa
            raise MultipleObjectsReturned
        if not preview and autor_instance.pk is None:
            if autor_instance.person.pk is None:
                autor_instance.person.save()
            autor_instance.save()
        return OrderedDict(
            [
                ('Person', p), ('Kürzel', kuerzel), ('instance', autor_instance)
            ]
        )
