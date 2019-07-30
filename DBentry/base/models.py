from inspect import isclass

from django.core import checks
from django.db import models
from django.utils.translation import gettext_lazy

from DBentry.fields import YearField
from DBentry.managers import CNQuerySet, MIZQuerySet
from DBentry.utils import get_model_fields

class BaseModel(models.Model):
    """
    Attributes related to searching:
    - search_fields: field names to include in searches.

    - primary_search_fields: any search result from a search on a field that is in search_fields but not in primary_search_fields 
        will be flagged as a 'weak hit' (.find()/autocomplete: and thus be visually separated from the other results). 

    - name_field: the name of the field that most accurately represents the record.
        If set, only this field will be fetched (and its values modified by search_fields_suffixes if applicable) from the database
        as search results.

    - search_fields_suffixes: a dictionary of search_fields and their suffixes that will be appended to search results 
        when using certain search strategies (queryset.find() or autocomplete views). 
        The suffixes will 'tell' the user why exactly they have found a particular result.

    - create_field: the name of the field for the dal autocomplete object creation
    """    
    search_fields = []
    primary_search_fields = []  
    search_fields_suffixes = {}
    
    name_field = None
    create_field = None
    exclude_from_str = ['beschreibung', 'bemerkungen']

    objects = MIZQuerySet.as_manager()

    def __str__(self):
        if self.name_field is not None:
            rslt = self._meta.get_field(self.name_field).value_from_object(self)
        else:
            rslt = " ".join([
                str(fld.value_from_object(self))
                for fld in get_model_fields(self._meta.model, foreign = False, m2m = False, exclude = self.exclude_from_str)
                if fld.value_from_object(self)
            ])
        return rslt.strip() or "---"

    def qs(self):
        """
        Returns a queryset that contains the current instance only.
        Counterpart to django.db.models.manager.ManagerDescriptor's __get__.
        """
        if isclass(self):
            # The user may inadvertently call qs() when working on the class level. This should be avoided, as the user may EXPECT a filtered queryset.
            raise AttributeError("Calling qs() from class level is prohibited. Use {}.objects instead.".format(self.__name__))
        else:
            return self._meta.model.objects.filter(pk=self.pk)

    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        """
        Returns the model's fields that are used in admin, autocomplete and advanced search form(? really?) searches.
        """
        #TODO: admin.get_search_fields tacks on a 'pk' search field (with a lookup)... should we do that *here* instead?
        if cls.search_fields:
            return cls.search_fields
        return [field.name for field in get_model_fields(cls, foreign = foreign, m2m = m2m)]
        #TODO: remove this! get_basefields does no longer exist..
        rslt = []
        for field in cls.get_basefields(as_string=True):
            if field not in rslt:
                rslt.append(field)
        return rslt

    class Meta:
        abstract = True
        default_permissions = ('add', 'change', 'delete', 'merge')

class BaseM2MModel(BaseModel):
    """
    Base class for models that implement an intermediary through table.
    """

    def __str__(self):
        data = []
        for ff in get_model_fields(self._meta.model, base=False, foreign=True, m2m=False):
            data.append(str(getattr(self, ff.name)))
        return "{} ({})".format(*data)

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_has_m2m_field(**kwargs))
        return errors

    @classmethod
    def _check_has_m2m_field(cls, **kwargs):
        """
        Checks for at least one of the related models of this intermediary table declaring a ManyToManyField through this table.
        While the ManyToManyField is not required for m2m to work, some features rely on there being one (f.ex. the crosslinks).
        """
        fk_fields = [f for f in cls._meta.get_fields() if f.concrete and f.is_relation and not f.many_to_many]
        found = False
        for fk_field in fk_fields:
            m2m_fields = get_model_fields(fk_field.related_model, base = False, foreign = False, m2m = True, primary_key = False)
            if any(m2m_field.remote_field.through == cls for m2m_field in m2m_fields):
                found = True
                break
        if not found:
            msg_text = "{model_name} represents an intermediary many-to-many table but no related model declares a ManyToManyField through this model."
            return [checks.Info(msg_text.format(model_name = cls._meta.model_name))]
        return []

    class Meta(BaseModel.Meta):
        abstract = True

class BaseAliasModel(BaseModel):
    """
    Base class for any model that implements a ManyToOne 'alias' relation using the `parent` field. 
    """
    alias = models.CharField('Alias', max_length = 100)
    parent = None   # the field that will hold the ForeignKey

    class Meta(BaseModel.Meta):
        verbose_name = 'Alias'
        verbose_name = 'Alias'
        abstract = True

class ComputedNameModel(BaseModel):   
    """
    Attributes related to the computed name:
    - _name_default: the default value for the _name field.
        If no name can be composed (missing data/new instance), this value will be used to display the object.

    - _name: the field that contains the 'name'. It's a step backwards in terms of database normalization in favour of
        being able to search for a computed name easily and quickly without having to instantiate a model object.

    - _changed_flag: if True, a new name will be computed the next time the model object is instantiated.

    - name_composing_fields: the names of fields whose data make up the name. 
        Values of these fields are retrieved from the database and passed to the _get_name method.
    """

    _name_default = gettext_lazy("No data for %(verbose_name)s.")

    _name = models.CharField(max_length=200, editable=False, default=_name_default)
    _changed_flag = models.BooleanField(editable=False, default=False)

    name_composing_fields = []

    exclude = ['_name', '_changed_flag', 'beschreibung', 'bemerkungen']

    name_field = '_name'

    objects = CNQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # An up-to-date name _may_ be expected upon initialization.
        self.update_name()

    def save(self, update = True, *args, **kwargs):
        super().save(*args, **kwargs)
        # parameters that make up the name may have changed, update name accordingly
        if update:
            self.update_name(force_update = True)

    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        # Include _name in the search_fields
        search_fields = super().get_search_fields(foreign, m2m)
        if '_name' not in search_fields:
            search_fields.insert(0,'_name')
        else:
            i = search_fields.index('_name')
            if i != 0:
                search_fields.pop(i)
                search_fields.insert(0,'_name')
        try:
            search_fields.remove('_changed_flag')
        except ValueError:
            pass
        return search_fields

    def update_name(self, force_update = False):
        """
        Updates the _name, if _changed_flag is True or if forced to.
        If the update is not aborted, the _changed_flag is always reset to False.

        Deferring the _name field will avoid an update, unless force_update is True.
        """
        deferred = self.get_deferred_fields()
        name_updated = False

        if not self.pk or '_name' in deferred and not force_update:
            # Abort the update if:
            # - this instance has not yet been saved to the database or 
            # - the _name field is not actually part of the instance AND 
            # - an update is not forced
            return name_updated

        if not '_changed_flag' in deferred:
            # _changed_flag was not deferred, self has access to it without calling refresh_from_db -- no need to hit the database
            changed_flag = self._changed_flag
        else:
            # avoid calling refresh_from_db by fetching the value directly from the database
            changed_flag = self.qs().values_list('_changed_flag', flat = True).get(pk = self.pk) #TODO: qs() followed by get() is redundant

        if force_update or changed_flag:
            # an update was scheduled or forced for this instance
            if not self.name_composing_fields:
                #TODO: this exception is never caught
                raise AttributeError("You must specify the fields that make up the name by listing them in name_composing_fields.")
            name_data = self.qs().values_dict(*self.name_composing_fields, flatten=True).get(self.pk) #TODO: qs() followed by get() is redundant
            current_name = self._get_name(**name_data)

            if self._name != current_name:
                # the name needs updating
                self.qs().update(_name= current_name)
                self._name = current_name
                name_updated = True

            if changed_flag:
                # We have checked whether or not the name needs updating; the changed_flag must be reset
                self.qs().update(_changed_flag=False)
                self._changed_flag = False
        return name_updated

    @classmethod
    def _get_name(cls, **kwargs):
        raise NotImplementedError('Subclasses must implement this method.')

    def __str__(self):
        return self._name % {'verbose_name':self._meta.verbose_name}

    class Meta(BaseModel.Meta):
        abstract = True
        ordering = ['_name']

class AbstractJahrModel(BaseModel):    
    jahr = YearField('Jahr')

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Jahr'
        verbose_name_plural = 'Jahre'
        ordering = ['jahr']

class AbstractURLModel(BaseModel):
    url = models.URLField(verbose_name = 'Webpage', blank = True)

    class Meta(BaseModel.Meta):
        abstract = True
        verbose_name = 'Web-Adresse'
        verbose_name_plural = 'Web-Adressen'
