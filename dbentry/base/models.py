from typing import Any, List

from django.core import checks, exceptions
from django.db import models
from django.utils.translation import gettext_lazy

from dbentry.fields import YearField
from dbentry.query import CNQuerySet, MIZQuerySet
from dbentry.utils import get_fields_and_lookups, get_model_fields


class BaseModel(models.Model):
    """
    BaseModel for all models of this app.

    Adds a 'merge' permission (required to be allowed to merge model instances)
    to the default permissions.

    Attributes:
        - ``name_field`` (str): the name of the field that most accurately
          represents the record. If set, the field's value will determine the
          output of __str__().
        - ``create_field`` (str): the name of the field for the dal
          autocomplete object creation.
        - ``exclude_from_str`` (list): list of field names to be excluded from
          the default __str__() implementation.
    """

    name_field: str = ''
    create_field: str = ''
    exclude_from_str: list = ['beschreibung', 'bemerkungen', '_fts']

    objects = MIZQuerySet.as_manager()

    def __str__(self) -> str:
        """
        Return a string representation of this instance.

        If 'name_field' is set, that field's value will be returned.
        Otherwise, the result will be a concatenation of values of all
        non-empty, non-relation fields that are not excluded through
        'exclude_from_str'.
        """
        # noinspection PyUnresolvedReferences
        opts = self._meta
        if self.name_field:
            result = str(opts.get_field(self.name_field).value_from_object(self))
        else:
            model_fields = get_model_fields(
                opts.model,
                foreign=False,
                m2m=False,
                exclude=self.exclude_from_str
            )
            # TODO: replace the above with the below to remove the get_model_fields call:
            # model_fields = [
            #     f for f in opts.get_fields()
            #     if f.concrete
            #     and not (f.primary_key or f.is_relation or f.name in self.exclude_from_str)
            # ]
            result = " ".join(
                [
                    str(fld.value_from_object(self))
                    for fld in model_fields
                    if fld.value_from_object(self)
                ]
            )
        return result.strip() or super().__str__()

    def qs(self) -> MIZQuerySet:
        """
        Return a queryset that contains the current instance only.

        Raises:
            TypeError: when qs() was called from class level. The method
                requires a model instance.
        """
        if isinstance(self, type):
            raise TypeError(
                f"Calling qs() from class level is prohibited. Use {self.__name__}.objects instead."
            )
        # noinspection PyUnresolvedReferences
        return self._meta.model.objects.filter(pk=self.pk)

    class Meta:
        abstract = True
        default_permissions = ('add', 'change', 'delete', 'merge', 'view')


class BaseM2MModel(BaseModel):
    """Base class for models that implement an intermediary through table."""

    def __str__(self) -> str:
        """
        Return a string representation of this instance.

        Combines the values of the ForeignKey fields of this model.
        """
        if self.name_field:
            return str(getattr(self, self.name_field))
        # noinspection PyUnresolvedReferences
        data = [
            # Collect the string representations of related objects.
            # getattr(self, fk_field.attname) and
            # fk_field.value_from_object(self) would only return the primary
            # key of the related object.
            str(getattr(self, fk_field.name))
            for fk_field in get_model_fields(
                self._meta.model, base=False, foreign=True, m2m=False
            )
            if not fk_field.null
        ]
        if len(data) < 2:
            # Cannot build a more meaningful representation than the default.
            return super().__str__()
        else:
            template = "{}" + " ({})" * (len(data) - 1)
            return template.format(*data)

    class Meta(BaseModel.Meta):
        abstract = True


class BaseAliasModel(BaseModel):
    """
    Abstract base class for any model that implements a ManyToOne 'alias'
    relation using the ``parent`` field.
    """

    alias = models.CharField('Alias', max_length=100)
    # the field that will hold the ForeignKey:
    parent: models.ForeignKey = None  # type: ignore[assignment]

    name_field = 'alias'

    class Meta(BaseModel.Meta):
        ordering = ['alias']
        verbose_name = 'Alias'
        verbose_name_plural = 'Aliases'
        abstract = True


class ComputedNameModel(BaseModel):
    """
    Abstract base model that manages a 'name' field for a given model instance.

    The 'name' is a concise description of a model instance. It is stored in
    the database to avoid repeated calculation and to make it accessible
    for queries on a database level.
    The value is reevaluated when an instance is saved or the ``_changed_flag``
    was set (either manually or by the ``CNQuerySet`` manager).

    It's a step backwards in terms of database normalization in favour of
    being able to search for a computed name easily and quickly on the
    database level without having to instantiate a model object.

    Attributes:
        - ``_name`` (CharField): the field that contains the computed name
        - ``name_default`` (str): the default value for the _name field, if no 
          name can be composed (missing data/new instance)
        - ``_changed_flag`` (boolean): if True, a new name will be computed the 
          next time the model object is instantiated
        - ``name_composing_fields`` (list): a sequence of names of fields
          whose data make up the name. Values of these fields are retrieved 
          from the database and passed to the '_get_name' method
    """

    _name_default: str = gettext_lazy("No data for %(verbose_name)s.")
    _name = models.CharField(max_length=200, editable=False, default=_name_default)
    _changed_flag = models.BooleanField(editable=False, default=False)

    name_composing_fields: list = []
    name_field: str = '_name'

    objects = CNQuerySet.as_manager()

    def __init__(self, *args, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # An up-to-date name _may_ be expected upon initialization.
        self.update_name()

    @classmethod
    def check(cls, **kwargs: Any) -> List[checks.CheckMessage]:
        errors = super().check(**kwargs)
        errors.extend(cls._check_name_composing_fields(**kwargs))
        return errors

    @classmethod
    def _check_name_composing_fields(cls, **_kwargs: Any) -> List[checks.CheckMessage]:
        """
        Check that name_composing_fields is set and does not contain invalid
        fields.
        """
        if not cls.name_composing_fields:
            return [
                checks.Warning(
                    "You must specify the fields that make up the name by "
                    "listing them in name_composing_fields.",
                    obj=cls.__name__
                )
            ]
        errors = []
        for field in cls.name_composing_fields:
            try:
                get_fields_and_lookups(cls, field)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError) as e:
                errors.append(
                    checks.Error(
                        "Attribute 'name_composing_fields' contains invalid item: "
                        "'%s'. %s" % (field, e),
                        obj=cls
                    )
                )
        return errors

    def save(self, update: bool = True, *args: Any, **kwargs: Any) -> None:
        """
        Save the current instance.

        If 'update' is true, force an update of the name field.
        """
        super().save(*args, **kwargs)
        if update:
            self.update_name(force_update=True)

    def update_name(self, force_update: bool = False) -> bool:
        """
        Update the ``_name``, if ``_changed_flag`` or ``force_update`` is True.

        If the update is not aborted, the ``_changed_flag`` is always reset to
        False. Deferring the name field will avoid an update, unless
        ``force_update`` is True.

        Returns True when the name was updated.
        """
        deferred = self.get_deferred_fields()

        if not self.pk or '_name' in deferred and not force_update:
            # Abort the update if:
            # - this instance has not yet been saved to the database or
            # - the _name field is not actually part of the instance AND
            # - an update is not forced
            return False

        if '_changed_flag' not in deferred:
            # _changed_flag was not deferred;
            # self has access to it without calling refresh_from_db.
            changed_flag = self._changed_flag
        else:
            # Avoid calling refresh_from_db by fetching the value directly
            # from the database:
            # noinspection PyUnresolvedReferences
            changed_flag = self._meta.model.objects.values_list(
                '_changed_flag', flat=True
            ).get(pk=self.pk)

        if force_update or changed_flag:
            # An update was scheduled or forced for this instance.
            name_data = self.qs().values_dict(
                *self.name_composing_fields, include_empty=False, flatten=False
            )
            current_name = self._get_name(**name_data[self.pk])

            if self._name != current_name:
                # Update the name and reset the _changed_flag.
                self.qs().update(_name=current_name, _changed_flag=False)
                self._name = current_name
                self._changed_flag = False
                return True
            if changed_flag:
                # The changed_flag was set, but the name did not need an update.
                # Reset the flag.
                self.qs().update(_changed_flag=False)
                self._changed_flag = False
        return False

    @classmethod
    def _get_name(cls, **kwargs: Any) -> str:
        """
        Compute the 'name' from keyword arguments provided.

        The keyword arguments are the fields of ``name_composing_fields``
        and their respective values.
        """
        raise NotImplementedError('Subclasses must implement this method.')  # pragma: no cover

    def __str__(self) -> str:
        # noinspection PyUnresolvedReferences
        return self._name % {'verbose_name': self._meta.verbose_name}

    class Meta(BaseModel.Meta):
        abstract = True
        ordering = ['_name']


class AbstractJahrModel(BaseModel):
    """Abstract model that adds a dbentry.fields.YearField."""

    jahr = YearField('Jahr')

    name_field = 'jahr'

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        ordering = ['jahr']


class AbstractURLModel(BaseModel):
    """Abstract model that adds an URLField."""

    url = models.URLField(verbose_name='Webpage', blank=True)

    name_field = 'url'

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Webseite'
        verbose_name_plural = 'Webseiten'
