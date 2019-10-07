from django.core import checks
from django.db import models
from django.utils.translation import gettext_lazy

from DBentry.fields import YearField
from DBentry.managers import CNQuerySet, MIZQuerySet
from DBentry.utils import get_model_fields


class BaseModel(models.Model):
    """
    BaseModel for all models of this app.

    Adds a 'merge' permission (required to be allowed to merge model instances)
    to the default permissions.

    Attributes:
        search_fields (tuple): field names to include in searches.
            (autocomplete, ModelAdmin search bar, queries using find())
        search_fields_suffixes (dict): a dictionary of search_fields and their
            suffixes that will be appended to search results when using certain
            search strategies (queryset.find() or autocomplete views).
            Through these suffixes it can be hinted at why exactly a user has
            found a particular result for a given search term.
        primary_search_fields (tuple): search results that were found through
            fields that are not in primary_search_fields will be flagged as
            a 'weak hit' and thus be visually separated from the other results.
        name_field (str): the name of the field that most accurately represents
            the record. If set, only this field will a) be used for __str__()
            and b) fetched from the database as search results for
            queryset.find().
        create_field (str): the name of the field for the dal autocomplete
            object creation.
        exclude_from_str (tuple): list of field names to be excluded from the
            default __str__() implementation.
    """

    search_fields = ()
    primary_search_fields = ()
    search_fields_suffixes = None
    name_field = None
    create_field = None
    exclude_from_str = ('beschreibung', 'bemerkungen')

    objects = MIZQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        if self.search_fields_suffixes is None:
            self.search_fields_suffixes = {}
        super().__init__(*args, **kwargs)

    def __str__(self):
        """
        Return a string representation of this instance.

        If 'name_field' is set, that field's value will be returned.
        Otherwise the result will be a concatenation of values of all non-empty,
        non-relation fields that are not excluded through 'exclude_from_str'.
        """
        if self.name_field is not None:
            rslt = self._meta.get_field(self.name_field).value_from_object(self)
        else:
            rslt = " ".join([
                str(fld.value_from_object(self))
                for fld in get_model_fields(
                    self._meta.model, foreign=False, m2m=False,
                    exclude=self.exclude_from_str
                )
                if fld.value_from_object(self)
            ])
        return rslt.strip() or "---"

    def qs(self):
        """Return a queryset that contains the current instance only."""
        try:
            # Use 'model.objects' instead of 'self.objects' as managers
            # are not accessible via instances.
            return self._meta.model.objects.filter(pk=self.pk)
        except TypeError:
            # qs() was called from class level; i.e. 'self' is a model class.
            # 'self.pk' thus refers to the property of that class which is not
            # the right type.
            raise TypeError(
                "Calling qs() from class level is prohibited. "
                "Use {}.objects instead.".format(self.__name__)
            )

    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        """Return the model's fields that are used in searches."""
        if cls.search_fields:
            return cls.search_fields
        return [
            field.name
            for field in get_model_fields(cls, foreign=foreign, m2m=m2m)
        ]

    class Meta:
        abstract = True
        default_permissions = ('add', 'change', 'delete', 'merge')


class BaseM2MModel(BaseModel):
    """Base class for models that implement an intermediary through table."""

    def __str__(self):
        """
        Return a string representation of this instance.

        Combines the values of the ForeignKey fields of this model.
        """
        data = [
            # Collect the string representations of related objects.
            # getattr(self, fk_field.attname) and fk_field.value_from_object(self)
            # would only return the primary key of the related object.
            str(getattr(self, fk_field.name))
            for fk_field in get_model_fields(
                self._meta.model, base=False, foreign=True, m2m=False
            )
            if not fk_field.null
        ]
        if len(data) < 2:
            # Cannot build a meaningful representation.
            return "---"
        else:
            template = "{}" + " ({})" * (len(data) - 1)
            return template.format(*data)

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_has_m2m_field(**kwargs))
        return errors

    @classmethod
    def _check_has_m2m_field(cls, **kwargs):
        """
        Check for at least one of the related models of this intermediary
        table declaring a ManyToManyField through this table. While the
        ManyToManyField is not required for m2m to work, some features rely
        on there being an explicit field on at least one side
        """
        # TODO: which features need an explicit ManyToManyField + BaseM2MModel.
        fk_fields = [
            f for f in cls._meta.get_fields()
            if isinstance(f, models.ForeignKey)
        ]
        # Walk through the ForeignKeys of this model and check if this model
        # represents the intermediary table for any of the related model's
        # ManyToManyFields.
        for fk_field in fk_fields:
            m2m_fields = (
                f for f in fk_field.related_model._meta.get_fields()
                if isinstance(f, models.ManyToManyField)
            )
            if any(field.remote_field.through == cls for field in m2m_fields):
                break
        else:
            # The loop completed without breaking:
            # no related model defines this model as an intermediary
            # for a ManyToMany relation.
            return [checks.Info(
                "{model_name} represents an intermediary many-to-many table "
                "but no related model declares a ManyToManyField through "
                "this model.".format(model_name=cls._meta.model_name)
            )]
        return []

    class Meta(BaseModel.Meta):
        abstract = True


class BaseAliasModel(BaseModel):
    """
    Abstract base class for any model that implements a
    ManyToOne 'alias' relation using the `parent` field.
    """

    alias = models.CharField('Alias', max_length=100)
    parent = None   # the field that will hold the ForeignKey

    class Meta(BaseModel.Meta):
        verbose_name = 'Alias'
        verbose_name = 'Alias'
        abstract = True


class ComputedNameModel(BaseModel):
    """
    Abstract base model that manages a 'name' field for a given model instance.

    The 'name' is a concise description of a model instance. It is stored in
    the database to avoid repeated calculation and to make it accessible
    for queries on a database level.
    The value is reevaluated when an instance is saved or the '_changed_flag'
    was set (either manually or by the 'CNQuerySet' manager).

    It's a step backwards in terms of database normalization in favour of
    being able to search for a computed name easily and quickly on the
    database level without having to instantiate a model object.

    Attributes related to the computed name:
        _name (CharField): the field that contains the computed name.
        name_default (str): the default value for the _name field, if no name
            can be composed (missing data/new instance).
        _changed_flag (boolean): if True, a new name will be computed the next
            time the model object is instantiated.
        name_composing_fields (tuple): a sequence of names of fields whose data
            make up the name. Values of these fields are retrieved from the
            database and passed to the '_get_name' method.
    """

    _name_default = gettext_lazy("No data for %(verbose_name)s.")
    _name = models.CharField(max_length=200, editable=False, default=_name_default)
    _changed_flag = models.BooleanField(editable=False, default=False)
    name_composing_fields = ()

    name_field = '_name'

    objects = CNQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # An up-to-date name _may_ be expected upon initialization.
        self.update_name()

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_name_composing_fields(**kwargs))
        return errors

    @classmethod
    def _check_name_composing_fields(cls, **kwargs):
        if not cls.name_composing_fields:
            return [checks.Warning(
                "You must specify the fields that make up the name by "
                "listing them in name_composing_fields."
            )]
        return []

    def save(self, update=True, *args, **kwargs):
        super().save(*args, **kwargs)
        # Parameters that make up the name may have changed;
        # update the name if necessary.
        if update:
            self.update_name(force_update=True)

    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        search_fields = super().get_search_fields(foreign, m2m)
        # Make '_name' the first search field.
        if '_name' not in search_fields:
            search_fields.insert(0, '_name')
        else:
            i = search_fields.index('_name')
            if i != 0:
                search_fields.pop(i)
                search_fields.insert(0, '_name')
        # Remove '_changed_flag' if it is in search_fields.
        # Searching for that field's value is nonsensical.
        try:
            search_fields.remove('_changed_flag')
        except ValueError:
            pass
        return search_fields

    def update_name(self, force_update=False):
        """
        Update the _name, if _changed_flag or force_update is True.

        If the update is not aborted, the _changed_flag is always reset to False.
        Deferring the _name field will avoid an update, unless force_update is True.
        Returns True when the _name was updated.
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
    def _get_name(cls, **kwargs):
        """
        Compute the 'name' from keyword arguments provided.

        The keyword arguments are the fields of 'name_composing_fields'
        and their respective values.
        """
        raise NotImplementedError('Subclasses must implement this method.')

    def __str__(self):
        return self._name % {'verbose_name': self._meta.verbose_name}

    class Meta(BaseModel.Meta):
        abstract = True
        ordering = ['_name']


class AbstractJahrModel(BaseModel):
    """Abstract model that adds a DBentry.fields.YearField."""

    jahr = YearField('Jahr')

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        ordering = ['jahr']


class AbstractURLModel(BaseModel):
    """Abstract model that adds an URLField."""

    url = models.URLField(verbose_name='Webpage', blank=True)

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Web-Adresse'
        verbose_name_plural = 'Web-Adressen'
