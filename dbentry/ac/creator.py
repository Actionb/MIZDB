from collections import OrderedDict
from typing import Any, Dict, Type, Union

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
            raise_exceptions (boolean): if false, return a ``FailedObject``
                dummy object instead, when encountering a
                MultipleObjectsReturned exception. Otherwise, let the exception
                bubble up
        """
        self.model = model
        self.raise_exceptions = raise_exceptions
        # noinspection PyProtectedMember,PyUnresolvedReferences
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
            # NOTE: raise_exceptions only addresses MultipleObjectsReturnedExceptions.
            # Is that intended?
            if self.raise_exceptions:
                raise e
            if preview:
                return {}
            # The dal view's post response expects an object with pk and
            # text attribute (which FailedObject emulates).
            return {'instance': FailedObject(str(e))}

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _get_model_instance(model: Type[Model], **data: Any) -> Model:
        """
        Query for existing model instances with kwargs ``data``.

        If the query returns exactly one instance, return that instance.
        If the query returned no results, return a new unsaved instance.
        Otherwise raise a MultipleObjectsReturned exception.
        """
        try:
            return model.objects.get(**data)
        except model.DoesNotExist:
            return model(**data)
        except model.MultipleObjectsReturned:
            raise MultipleObjectsReturned

    def create_person(self, text: Union[str, HumanName], preview: bool = True) -> OrderedDict:
        """
        Get or create a Person instance from ``text``.

        If ``preview`` is True, do not save the instance even if it is new.

        Returns:
            OrderedDict that includes the created instance and additional
                information for the 'create_option' of a dal widget
        """
        # parse_name will join first and middle names
        vorname, nachname = parse_name(text)
        person_instance = self._get_model_instance(
            _models.Person, vorname=vorname, nachname=nachname
        )
        if not preview and person_instance.pk is None:
            person_instance.save()
        return OrderedDict(
            [
                ('Vorname', vorname), ('Nachname', nachname),
                ('instance', person_instance)
            ]
        )

    def create_autor(self, text: str, preview: bool = True):
        """
        Get or create an autor instance from ``text``.

        If ``preview`` is True, do not save the instance even if it is new.

        Returns:
            OrderedDict that includes the created instance and additional
                information for the 'create_option' of a dal widget
        """
        name = HumanName(text)
        kuerzel = name.nickname
        name.nickname = ''
        p = self.create_person(name, preview)
        person_instance = p.get('instance')
        autor_instance = self._get_model_instance(
            _models.Autor, person=person_instance, kuerzel=kuerzel
        )
        if not preview and autor_instance.pk is None:
            # noinspection PyUnresolvedReferences
            if autor_instance.person.pk is None:
                # noinspection PyUnresolvedReferences
                autor_instance.person.save()
            autor_instance.save()
        return OrderedDict(
            [
                ('Person', p), ('Kürzel', kuerzel), ('instance', autor_instance)
            ]
        )
