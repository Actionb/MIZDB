from django.db import models
from django.utils.translation import gettext_lazy

from DBentry.managers import MIZQuerySet, CNQuerySet

def get_model_fields(model, base = True, foreign = True, m2m = True, exclude = (), primary_key = False):
    rslt = []
    for f in model._meta.get_fields():
        if not f.concrete or f in exclude:
            continue
        if f.primary_key and not primary_key:
            continue
        if f.is_relation:
            if f.many_to_many:
                if m2m:
                    rslt.append(f)
            elif foreign:
                rslt.append(f)
        elif base:
            rslt.append(f)
    return rslt
            
def get_model_relations(model, forward = True, reverse = True):
    m2m_models = set(
        f.remote_field.through if f.concrete else f.through
        for f in model._meta.get_fields() 
        if f.many_to_many
    )
    rslt = set()
    for f in model._meta.get_fields():
        if not f.is_relation:
            continue
        if f.concrete:
            if not forward:
                # We do not want any relation fields that are declared on this model.
                continue
            rslt.add(f.remote_field) # add the actual RELATION, not the ForeignKey/ManyToMany field
        else:
            if not reverse:
                # We do not want any reverse relations. 
                continue
            if f.one_to_many and f.related_model in m2m_models:
                # This is a 'reverse' ForeignKey relation from an actual (i.e. not auto_created) m2m intermediary model to 'model'.
                # The relation between the intermediary model and this 'model' was realized on *both* sides, hence 
                # it shows up twice (as a ManyToOneRel and a ManyToManyRel).
                # The ManyToManyRel contains all the information we need so we ignore the ManyToOneRel.
                continue
            rslt.add(f)
    return list(rslt)

class BaseModel(models.Model):
    #TODO: exclude attribute does not do what the description says, it excludes fields from the 'field collection' methods as well!
    """
    Attributes related to searching:
    - exclude: field names to exclude from searches 
    
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
    exclude = ['beschreibung', 'bemerkungen'] 
    
    search_fields = []
    
    primary_search_fields = []  
    
    name_field = None
    
    search_fields_suffixes = {}
    
    create_field = None
    
    objects = MIZQuerySet.as_manager()
    
    def _show(self):
        rslt = ""
        for fld_name in self.get_basefields(as_string = True):
            if getattr(self, fld_name, False):
                rslt +=  "{} ".format(str(getattr(self, fld_name)))
        if rslt:
            return rslt.strip()
        else:
            return "---"
            
    def __str__(self):
        return self._show()
        
    def qs(self):
        """
        Returns a queryset that contains the current instance only.
        Counterpart to django.db.models.manager.ManagerDescriptor's __get__.
        """
        from inspect import isclass
        if isclass(self):
            # The user may inadvertently call qs() when working on the class level. This should be avoided, as the user may EXPECT a filtered queryset.
            raise AttributeError("Calling qs() from class level is prohibited. Use {}.objects instead.".format(self.__name__))
        else:
            return self._meta.model.objects.filter(pk=self.pk)
    
    @classmethod
    def get_basefields(cls, as_string=False):
        """
        Returns the model's fields that are not the primary key, a relation or in the model's exclude list.
        Works much like cls._meta.concrete fields.
        """
        return [i.name if as_string else i for i in cls._meta.fields
            if i != cls._meta.pk and not i.is_relation and not i.name in cls.exclude]
        
    @classmethod
    def get_foreignfields(cls, as_string=False):
        """
        Returns the model's fields that represent a ForeignKey and are NOT in the model's exclude list.
        """
        return [i.name if as_string else i for i in cls._meta.fields if isinstance(i, models.ForeignKey) and not i.name in cls.exclude]
        
    @classmethod
    def get_m2mfields(cls, as_string=False):
        """
        Returns the model's fields that represent a ManyToXField and are NOT in the model's exclude list.
        """
        return [i.name if as_string else i for i in cls._meta.get_fields() if (not isinstance(i, models.ForeignKey) and i.is_relation) and not i.name in cls.exclude] 
        
    @classmethod
    def get_reverse_relations(cls):
        """
        Returns all relation objects that represent a reverse relation to this model.
        """
        return [f for f in cls._meta.get_fields() if f.is_relation and not f.concrete]
        
        
    @classmethod
    def get_required_fields(cls, as_string=False):
        """
        Returns the model's fields that are required.
        """
        #TODO: fld.null check?
        rslt = []
        for fld in cls._meta.fields:
            if not fld.auto_created and fld.blank == False:
                if not fld.has_default() or fld.get_default() is None: 
                    # fld either has no default or the default is None
                    if as_string:
                        rslt.append(fld.name)
                    else:
                        rslt.append(fld)
        return rslt
    
    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        """
        Returns the model's fields that are used in admin, autocomplete and advanced search form(? really?) searches.
        """
        if cls.search_fields:
            return cls.search_fields
        rslt = []
        for field in cls.get_basefields(as_string=True):
            if field not in rslt:
                rslt.append(field)
        return rslt
        
    def get_updateable_fields(self):
        """
        Returns the self's fields (as their names) that are empty or have their default value.
        Used by merge_records.
        """
        rslt = []
        for fld in self._meta.get_fields():
            if fld.concrete and not fld.name.startswith('_'): # exclude 'private' fields
                value = fld.value_from_object(self)
                if value in fld.empty_values:
                    # This field's value is 'empty' in some form or other
                    rslt.append(fld.name)
                else:
                    default = fld.default if not fld.default is models.fields.NOT_PROVIDED else None
                    if default is not None:
                        # fld.default is a non-None value, see if the field's value differs from it
                        if type(default) is bool:
                            # Special case, boolean values should be left alone?
                            continue
                        elif default == value:
                            # This field has it's default value as value:
                            rslt.append(fld.name)
                        elif default in fld.choices and fld.choices[default][0] == value:
                            # This field has it's default choice as a value
                            rslt.append(fld.name)
        return rslt
        
    class Meta:
        abstract = True
        default_permissions = ('add', 'change', 'delete', 'merge')
        
class BaseM2MModel(BaseModel):
    """
    Base class for models that implement an intermediary through table.
    """
    
    def _show(self):
        data = []
        for ff in self.get_foreignfields(True):
            data.append(str(getattr(self, ff)))
        return "{} ({})".format(*data)
            
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
            changed_flag = self.qs().values_list('_changed_flag', flat = True).get(pk = self.pk)
            
        if force_update or changed_flag:
            # an update was scheduled or forced for this instance
            
            if not self.name_composing_fields:
                raise AttributeError("You must specify the fields that make up the name by listing them in name_composing_fields.")
            name_data = self.qs().values_dict(*self.name_composing_fields, flatten=True).get(self.pk)
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
