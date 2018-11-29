import time
import calendar
import datetime
from collections import Iterable
from urllib.parse import parse_qs

from nameparser import HumanName

from django.db import transaction, models
from django.db.utils import IntegrityError

from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.text import capfirst

from django.urls import reverse, NoReverseMatch

from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename

from .constants import M2M_LIST_MAX_LEN
from .logging import get_logger

##############################################################################################################
# model utilities
############################################################################################################## 
    
def get_model_from_string(model_name):
    from django.apps import apps 
    try:
        return apps.get_model('DBentry', model_name)
    except LookupError:
        return None

def get_model_fields(model, base = True, foreign = True, m2m = True, exclude = (), primary_key = False):
    rslt = []
    for f in model._meta.get_fields():
        if not f.concrete or f.name in exclude:
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
    
    relation_fields = [f for f in model._meta.get_fields() if f.is_relation]
    # ManyToManyRels can always be regarded as symmetrical (both 'forward' and 'reverse') and should always be included 
    rslt = set(f.remote_field if f.concrete else f for f in relation_fields if f.many_to_many)
    for f in relation_fields:
        if f.concrete:
            if forward:
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
        
def get_relation_info_to(model, rel):
    """
    Returns:
    - the model that holds the related objects
        (rel.through if many_to_many else rel.related_model)
    - the field that realizes relation 'rel' towards direction 'model' 
        (the field of the m2m table table pointing to model if many_to_many else the ForeignKey field i.e. rel.field)
    """
    if rel.many_to_many:
        related_model = rel.through
        m2m_field = rel.field
        if m2m_field.model == model:
            # The ManyToManyField is with model:
            # the source accessor/field pointing back to model on the m2m table can be retrieved via m2m_field_name()
            related_field = related_model._meta.get_field(m2m_field.m2m_field_name())
        else:
            # The ManyToManyField is with the *other* model:
            # the related accessor/field pointing to model on the m2m table can be retrieved via m2m_reverse_field_name()
            related_field = related_model._meta.get_field(m2m_field.m2m_reverse_field_name())
    else:
        related_model = rel.related_model
        related_field = rel.field
    return related_model, related_field
    
def get_required_fields(model):
    """
    Returns the fields of a model that require a value.
    """
    rslt = []
    for f in get_model_fields(model, m2m = False):
        if f.null:
            continue
        if f.blank and isinstance(f, (models.CharField, models.TextField)):
            # String-based fields should not have null = True, hence checking the less meaningful blank attribute
            continue
        if f.has_default():
            # Field has a default value, whether or not that value is an 'EMPTY_VALUE' we do not care
            continue
        rslt.append(f)
    return rslt
    
def get_related_descriptor(model_class, rel):
    """
    Returns the descriptor that describes relation rel referenced from model model_class.
    """
    if rel.many_to_many:
        if rel.field.model == model_class:
            # model_class contains the ManyToManyField declaring the relation
            attr = rel.field.name
        else:
            attr = rel.get_accessor_name()
        descriptor = getattr(model_class, attr)
    else:
        descriptor = getattr(rel.model, rel.get_accessor_name())
    return descriptor

def get_related_manager(instance, rel):
    """
    Returns the related manager that governs the relation rel for model object instance.
    """
    descriptor = get_related_descriptor(instance._meta.model, rel)
    if not rel.many_to_many and rel.field.model == instance._meta.model:
        # If rel is a forward ManyToOneRel, we must call the related_manager_cls with the related object
        return descriptor.related_manager_cls(getattr(instance, rel.field.name))
    return descriptor.related_manager_cls(instance)

def get_updateable_fields(instance):
    """
    Returns the names of instance's fields that are empty or have their default value.
    Used by merge_records.
    """
    rslt = []
    for fld in get_model_fields(instance._meta.model, m2m = False, primary_key = False):
        if not fld.concrete or fld.name.startswith('_'):
            # Exclude 'private' fields
            continue
        field_value = fld.value_from_object(instance)
        if field_value in fld.empty_values:
            # This field's value is 'empty' in some form or other
            rslt.append(fld.attname)
        elif fld.has_default():
            if type(fld.default) is bool:
                # Special case, boolean values should be left alone?
                continue
            elif fld.default == field_value:
                # This field has it's default value/choice
                rslt.append(fld.attname)
    return rslt

def is_protected(objs, using='default'):
    """
    Returns a models.ProtectedError if any of the objs are protected through a ForeignKey, otherwise returns None.
    """
    # Used by merge_records
    collector = models.deletion.Collector(using='default')
    try:
        collector.collect(objs)
    except models.ProtectedError as e:
        return e


def merge_records(original, qs, update_data = None, expand_original = True, request = None):
    """ Merges original object with all other objects in qs and updates original's values with those in update_data. 
        Returns the updated original.
    """
    logger = get_logger(request)
    
    qs = qs.exclude(pk=original.pk)
    model = original._meta.model
    original_qs = model.objects.filter(pk=original.pk)
    with transaction.atomic():
        if expand_original:
            if update_data is None:
                update_data = {} # Avoid mutable default arguments shenanigans
                updateable_fields = get_updateable_fields(original)
                for other_record_valdict in qs.values(*updateable_fields):
                    for k, v in other_record_valdict.items():
                        if v and k not in update_data:
                            update_data[k] = v
            
            # Update the original object with the additional data and log the changes.
            original_qs.update(**update_data)
            logger.log_update(original_qs, update_data)
            
        for rel in get_model_relations(model, forward = False):
            related_model, related_field = get_relation_info_to(model, rel)
            # All the related objects that are going to be updated to be related to original
            merger_related = related_model.objects.filter(**{related_field.name + '__in':qs})
            qs_to_be_updated = merger_related.all()
            if not qs_to_be_updated.exists():
                continue
            
            # exclude all related objects that the original has already, avoiding IntegrityError due to UNIQUE CONSTRAINT violations
            for unique_together in related_model._meta.unique_together:
                if related_field.name in unique_together:
                    # The ForeignKey field is part of this unique_together, remove it or
                    # we will later do exclude(FKfield_id=original_id,<other_values>) which would not actually exclude anything.
                    unique_together = list(unique_together)
                    unique_together.remove(related_field.name)
                    if not unique_together:
                        continue
                # Nothing will get excluded from the qs with related_field = original as no objects in the qs are related to original yet.
                for values in related_model.objects.filter(**{related_field.name:original}).values(*unique_together):
                    qs_to_be_updated = qs_to_be_updated.exclude(**values)

                
            
            # The ids of the related objects that have been updated. By default this encompasses all objects in qs_to_be_updated.
            # If an IntegrityError still occurs, this list is reevaluated.
            updated_ids = list(qs_to_be_updated.values_list('pk', flat = True))
            try:
                with transaction.atomic():
                    qs_to_be_updated.update(**{related_field.name:original})
            except IntegrityError:
                # I fucked up. An object that the original already has was left in qs_to_be_updated.
                # Work through each object in qs_to_be_updated and do the update individually.
                updated_ids = []
                for id in qs_to_be_updated.values_list('pk', flat=True):
                    loop_qs = related_model.objects.filter(pk=id)
                    try:
                        with transaction.atomic():
                            loop_qs.update(**{related_field.name:original})
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations
                        pass
                    else:
                        updated_ids.append(id)
            
            # Log the changes
            for id in updated_ids:
                obj = related_model.objects.get(pk=id)
                logger.log_addition(original, obj) # log the addition of a new related object for original
                logger.log_change(obj, related_field.name, original) # log the change of the related object's relation field pointing towards original
                
            if rel.on_delete == models.PROTECT:
                not_updated = merger_related.exclude(pk__in=updated_ids)
                if not_updated.exists() and not is_protected(not_updated):
                    # Some related objects could not be updated (probably because the original already has identical related objects)
                    # delete the troublemakers?
                    logger.log_delete(not_updated)
                    not_updated.delete()
        
        # All related objects that could have been protected should now have been moved to 'original'.
        # We can now check if any of the merged objects are still protected.
        protected = is_protected(qs)
        if protected:
            # Some objects are still protected, abort the merge through a rollback
            raise protected
        logger.log_delete(qs)
        qs.delete()
    return original_qs.first(), update_data
         
def get_relations_between_models(model1, model2): 
    """ 
    Returns the field and the relation object that connects model1 and model2. 
    """ 
    # used by signals.set_name_changed_flag_ausgabe
    if isinstance(model1, str): 
        model1 = get_model_from_string(model1) 
    if isinstance(model2, str): 
        model2 = get_model_from_string(model2) 
     
    field = None # the concrete field declaring the relation 
    rel = None # the reverse relation 
    for fld in model1._meta.get_fields(): 
        if fld.is_relation and fld.related_model == model2: 
            if fld.concrete: 
                field = fld 
            else: 
                rel = fld 
            break 
                 
    for fld in model2._meta.get_fields(): 
        if fld.is_relation and fld.related_model == model1: 
            if fld.concrete: 
                field = fld 
            else: 
                rel = fld 
            break 
     
    return field, rel 
    
def get_full_fields_list(model):
    rslt = set()
    for field in get_model_fields(model):
        rslt.add(field.name)
    for rel in get_model_relations(model, forward = False): # forward relations already handled by get_model_fields
        if rel.many_to_many and rel.field.model == model:
            rslt.add(rel.field.name)
        else:
            rslt.add(rel.name)
    return rslt
    
def get_all_model_names():
    """
    Returns all the names of models in the apps registry that are subclasses of DBentry.base.models.BaseModel.
    """
    from django.apps import apps 
    from DBentry.base.models import BaseModel
    
    mdls = apps.get_models('DBentry')
    my_mdls = [m._meta.model_name for m in mdls if issubclass(m, BaseModel)]
    return sorted(my_mdls, key = lambda m: m.lower())
    
    

##############################################################################################################
# text utilities
##############################################################################################################
def concat_limit(values, width = M2M_LIST_MAX_LEN, sep = ", ", z = 0):
    """
    Joins string values of iterable 'values' up to a length of 'width', truncating the remainder.
    """
    if not values:
        return ''
    rslt = str(values[0]).zfill(z)
    for v in values[1:]:
        if len(rslt) + len(str(v))<width:
            rslt += sep + str(v).zfill(z)
        else:
            rslt += sep + "[...]"
            break
    return rslt
    
def snake_case_to_spaces(value):
    return value.replace('_', ' ').strip()
    
def coerce_human_name(full_name):
    if not isinstance(full_name, (str, HumanName)):
        full_name = str(full_name)
    if isinstance(full_name, str):
        full_name = full_name.strip()
        if len(full_name.split()) == 1:
            # 'full_name' only contains a last name, 'trick' nameparser to treat it as such
            full_name = full_name + ","
        hn = HumanName(full_name)
    else:
        hn = full_name
    return hn
    
def parse_name(full_name):
    hn = coerce_human_name(full_name)
    return " ".join([hn.first, hn.middle]).strip(), hn.last
    
def parse_cl_querystring(query_string):
    """
    Takes the full query string containing the preserved filters of a changelist and returns 
    those as a dictionary.
    Example:
        - query_string: '_changelist_filters=ausgabe__magazin%3D326%26ausgabe%3D14962'
        - returns: {'ausgabe__magazin': ['326'], 'ausgabe': ['14962']}
    """
    # Retrieve the _changelist_filters bit of the query_string: {'_changelist_filters': ['ausgabe__magazin=326&ausgabe=14962']}
    cl_filters = parse_qs(query_string).get('_changelist_filters', None)
    if not cl_filters:
        return {}
    # And parse the filters again: {'ausgabe__magazin': ['326'], 'ausgabe': ['14962']}
    return parse_qs(cl_filters[0])
    
##############################################################################################################
# admin utilities
############################################################################################################## 
def get_obj_link(obj, user, site_name='admin', include_name=True): #TODO: include_name == include_label??
    opts = obj._meta
    no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
                               force_text(obj))

    try:
        admin_url = reverse('%s:%s_%s_change'
                            % (site_name,
                               opts.app_label,
                               opts.model_name),
                            None, (quote(obj._get_pk_val()),))
    except NoReverseMatch:
        # Change url doesn't exist -- don't display link to edit
        return no_edit_link

    p = '%s.%s' % (opts.app_label,
                   get_permission_codename('change', opts))
    if not user.has_perm(p):
        return no_edit_link
    # Display a link to the admin page.
    if include_name:
        link = format_html('{}: <a href="{}">{}</a>', # include_name is more a label than... a 'name'
                           capfirst(opts.verbose_name),
                           admin_url,
                           obj)
    else:
        link = format_html('<a href="{}">{}</a>',
                           admin_url,
                           obj)           
    return link
    
def link_list(request, obj_list, SEP = ", "):
    """ Returns a string with html links to the objects in obj_list separated by SEP.
        Used in ModelAdmin
    """
    links = []
    for obj in obj_list:
        links.append(get_obj_link(obj, request.user, include_name=False))
    return format_html(SEP.join(links))
    
def get_model_admin_for_model(model, *admin_sites):
    from DBentry.sites import miz_site
    if isinstance(model, str):
        model = get_model_from_string(model)
    sites = admin_sites or [miz_site]
    for site in sites:
        if site.is_registered(model):
            return site._registry.get(model)        

def has_admin_permission(request, model_admin):
    if not model_admin.has_module_permission(request):
        return False
    perms = model_admin.get_model_perms(request)

    # Check whether user has any perm for this module.
    return True in perms.values()
    
def make_simple_link(url, label, is_popup, as_listitem = False):
    if is_popup:
        template = '<a href="{url}?_popup=1" onclick="return popup(this)">{label}</a>'
    else:
        template = '<a href="{url}" target="_blank">{label}</a>'
    if as_listitem:
        template = '<li>' + template + '</li>'
    return format_html(
        template, 
        url = url, 
        label = label
    )
    

##############################################################################################################
# general utilities
##############################################################################################################
def flatten_dict(d, exclude=[]):
    rslt = {}
    for k, v in d.items():
        if isinstance(v, dict):
            rslt[k] = flatten_dict(v, exclude)
        elif k not in exclude and isinstance(v, Iterable) and not isinstance(v, str) and len(v)==1:
            rslt[k] = v[0]
        else:
            rslt[k] = v
    return rslt

def is_iterable(obj):
    return isinstance(obj, Iterable) and not isinstance(obj, (bytes, str))

def split_field(field_name, data, separators = [',']):
    """ Splits the content of data[field_name] according to separators and merges the new values back into a list of dicts."""
    if not data.get(field_name):
        return [data]
    rslt = []
    data_rest = {k:v for k, v in data.items() if k != field_name}
    for d in set(recmultisplit(data.get(field_name, ''), separators)):
        x = data_rest.copy()
        x.update({field_name:d})
        rslt.append(x)
    return rslt
    
def recmultisplit(values, separators = []):
    """Splits a string at each occurence of s in separators."""
    if len(separators)==1:
        return [i.strip() for i in values.split(separators[0])]
    rslt = []
    seps = separators[:]
    sep = seps.pop()
    
    for x in values.split(sep):
        rslt += recmultisplit(x, seps)
    return rslt   

##############################################################################################################
# date utilities
##############################################################################################################
def leapdays(start, end):
    # calendar.leapdays ignores the leap day if start.year == end.year and start.year is a leap year
    # it also ignores the leapday if the end date is in a leap year and the date is passed the leap day
    if start > end:
        start, end = end, start
            
    start_leap = end_leap = None
    if calendar.isleap(start.year):
        start_leap = datetime.date(start.year, 2, 29)
    if calendar.isleap(end.year):
        end_leap = datetime.date(end.year, 2, 29)
    
    if start.year == end.year:
        if start_leap and start < start_leap and end >= start_leap:
            return 1
        return 0
        
    leapdays = calendar.leapdays(start.year, end.year) # end year is EXCLUSIVE 
    if start_leap and start >= start_leap:
        # calendar.leapdays would count the leap day of the start year even if the start date lies after the leap day
        leapdays -= 1
    if end_leap and end >= end_leap:
        # calendar.leapdays treats the end year exclusively, i.e. it counts the leap days UP to that year
        # if the end date lies after the leap day, we must include it
        leapdays += 1
    return leapdays
    
def build_date(years, month_ordinals, day = None):
    if not is_iterable(years):
        years = [years]
    if not is_iterable(month_ordinals):
        month_ordinals = [month_ordinals]
        
    # Filter out None values that may have been returned by a values_list call
    none_filter = lambda x: x is not None
    years = list(filter(none_filter,  years))
    month_ordinals = list(filter(none_filter, month_ordinals))
    
    if not (years and month_ordinals):
        # either years or month_ordinals is an empty sequence
        return
    year = min(years)
    month = min(month_ordinals)
    
    if len(month_ordinals) > 1:
        # If the ausgabe spans several months, use the last day of the first appropriate month
        # to chronologically order it after any ausgabe that appeared 'only' in that first month
        if len(years) > 1:
            # the ausgabe spans two years, assume the latest month for the e_datum
            month = max(month_ordinals)
        # Get the last day of the chosen month
        day = calendar.monthrange(year, month)[1]
        
    if day is None:
        day = 1
        
    return datetime.date(
        year = year, 
        month = month, 
        day = day, 
    )

##############################################################################################################
# debug utilities
############################################################################################################## 
def timethis(func, *args, **kwargs):
    ts = time.time()
    func(*args, **kwargs)
    te = time.time()
    return te - ts
    
def num_queries(func=None, *args, **kwargs):
    from django.test.utils import CaptureQueriesContext
    from django.db import connections, DEFAULT_DB_ALIAS
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    conn = connections[using]

    context = CaptureQueriesContext(conn)
    if func is None:
        # return the context manager so the caller can use it 
        return context

    with context as n:
        func(*args, **kwargs)
    return len(n)
    
def debug_queryfunc(func, *args, **kwargs):
    with num_queries() as n:
        t = timethis(func, *args, **kwargs)
    n = len(n)
    print("Time:", t)
    print("Num. queries:", n)
    return t, n
