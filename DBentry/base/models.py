from django.db import models
from django.utils.translation import gettext_lazy
from django.utils.functional import cached_property

from DBentry.managers import AusgabeQuerySet, MIZQuerySet        

class BaseModel(models.Model):  
    #TODO: Meta.attribute/property/get_exclude_fields? Right now, every class that defines exclude overwrites this base list -- which may not be such a bad thing
    exclude = ['info', 'beschreibung', 'bemerkungen']                #field names to exclude from searches 
    search_fields = []          # related fields to be included in searches
    
    objects = MIZQuerySet.as_manager()
    
    @cached_property
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
        return self._show
        
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
    def get_required_fields(cls, as_string=False):
        """
        Returns the model's fields that are required.
        """
        #TODO: fld.null check?
        #NOTE: Shouldn't it be: NOT fld.get_default() is None ??
        rslt = []
        for fld in cls._meta.fields:
            if not fld.auto_created and fld.blank == False:
                if not fld.has_default() or fld.get_default() is None: 
                    if as_string:
                        rslt.append(fld.name)
                    else:
                        rslt.append(fld)
        return rslt
    
    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        """
        Returns the model's fields that are used in admin, autocomplete and advanced search form searches.
        """
        #TODO: check if all cls.search_fields are of this model
        rslt = set(list(cls.search_fields) + cls.get_basefields(as_string=True))
        if foreign:
            for fld in cls.get_foreignfields():
                for rel_fld in fld.related_model.get_search_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        if m2m:
            for fld in cls.get_m2mfields():
                for rel_fld in fld.related_model.get_search_fields():
                    rslt.add("{}__{}".format(fld.name, rel_fld))
        return rslt
        
    def get_updateable_fields(obj):
        """
        Returns the obj's fields (as their names) that are empty or have their default value.
        Used by merge_records.
        """
        rslt = []
        for fld in obj._meta.get_fields():
            if fld.concrete and not fld.name.startswith('_'): # exclude 'private' fields
                value = fld.value_from_object(obj)
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

    _name = models.CharField(max_length=200, editable=False, default=gettext_lazy("No data."))
    _changed_flag = models.BooleanField(editable=False, default=False)
    
    exclude = ['_name', '_changed_flag', 'info', 'beschreibung', 'bemerkungen']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # An up-to-date name _may_ be expected upon initialization.
        self.update_name()
             
    def save(self, update = False, *args, **kwargs):
        super().save(*args, **kwargs)
        # parameters that make up the name may have changed, update name accordingly
        if update:
            self.update_name(force_update = True)
    
    @classmethod
    def get_search_fields(cls, foreign=False, m2m=False):
        # Include _name in the search_fields
        search_fields = super().get_search_fields(foreign, m2m)
        search_fields.add('_name')
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
            #TODO: or rather when ANY fields are in deferred? This would stop stop updating entirely when using .only()
            #TODO: self.pk == None and force_update == True: raise an exception to warn the user that the object cannot be accessed via querysets if it hasnt been stored to the database
            # Abort the update if:
            # - this instance has not yet been saved to the database or 
            # - the _name field is no actually part of the instance AND 
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
            
            # Pass data to construct a name to get_name. Fetch data from the database if any fields are deferred to avoid calls to refresh_from_db.
            name_data = dict(*self.qs.values(*deferred)) if deferred else {}
            current_name = self.get_name(**name_data)
            
            fields_to_refresh = []
            
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
        
    def get_name(self, **kwargs):
        raise NotImplementedError('Subclasses must implement this method.')
    
    def __str__(self):
        return self._name
                    
    class Meta(BaseModel.Meta):
        abstract = True
