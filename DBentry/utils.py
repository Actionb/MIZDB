import re
import time
from collections import Iterable

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

def is_protected(objs, using='default'):
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
    original_qs = original._meta.model.objects.filter(pk=original.pk)
    with transaction.atomic():
        if expand_original:
            if update_data is None:
                update_data = {} # Avoid mutable default arguments shenanigans
                updateable_fields = original.get_updateable_fields()
                for other_record_valdict in qs.values(*updateable_fields):
                    for k, v in other_record_valdict.items():
                        if v and k not in update_data:
                            update_data[k] = v
                            
            original_qs.update(**update_data)
            logger.log_update(original_qs, update_data)
            
        for rel in original._meta.related_objects:
            related_model = rel.field.model
            val_list = qs.values_list(rel.field.target_field.name)
            # These are the objects of the related_model that will be deleted after the merge
            # See if there are any values that the original does not have 
            related_qs = related_model.objects.filter(**{ rel.field.name + '__in' : val_list })
            
            if rel.many_to_many:
                m2m_model = rel.through
                pk_name = m2m_model._meta.pk.name
                if rel.to == original._meta.model: #m2m_model._meta.get_field(rel.field.m2m_field_name()).model == original._meta.model
                    # rel points from original to related_model (ManyToManyField is on original)
                    to_original_field_name = rel.field.m2m_reverse_field_name()
                    to_related_field_name = rel.field.m2m_field_name()
                else:
                    # rel points from related_model to original (ManyToManyField is on related_model)
                    to_original_field_name = rel.field.m2m_field_name()
                    to_related_field_name = rel.field.m2m_reverse_field_name()
                to_update = m2m_model.objects.filter(**{to_related_field_name+'__in':related_qs}).values_list(pk_name, flat=True)
                
                for id in to_update:
                    loop_qs = m2m_model.objects.filter(pk=id)
                    try:
                        with transaction.atomic():
                            loop_qs.update(**{to_original_field_name:original})
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations
                        pass
                    else:
                        logger.log_update(loop_qs, to_original_field_name)
            else:
                for i in related_qs:
                    try:
                        with transaction.atomic():
                            getattr(original, rel.get_accessor_name()).add(i)
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations
                        pass
                    else:
                        logger.log_add(original, rel, i)
                        
        logger.log_delete(qs)
        qs.delete()
    return original_qs.first(), update_data
    
def concat_limit(values, width = M2M_LIST_MAX_LEN, sep = ", ", z = 0):
    """
        Joins string values of iterable 'values' up to a length of 'width'.
    """
    #TODO: use django.utils.text.Truncate
    if not values:
        return ''
    rslt = str(values[0]).zfill(z)
    for c, i in enumerate(values[1:], 1):
        if len(rslt) + len(str(i))<width:
            rslt += sep + str(i).zfill(z)
        else:
            rslt += sep + "[...]"
            break
    return rslt
        
def get_obj_link(obj, user, site_name='admin', include_name=True):
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
        link = format_html('{}: <a href="{}">{}</a>',
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
    
def model_from_string(model_name):
    from django.apps import apps 
    try:
        return apps.get_model('DBentry', model_name)
    except LookupError:
        return None
#TODO: rename model_from_string to get_model_from_string
get_model_from_string = model_from_string

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
         
def get_relations_between_models(model1, model2): 
    """ 
    Returns the field and the relation object that connects model1 and model2. 
    """ 
    if isinstance(model1, str): 
        model1 = model_from_string(model1) 
    if isinstance(model2, str): 
        model2 = model_from_string(model2) 
     
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

def timethis(func, *args, **kwargs):
    ts = time.time()
    r = func(*args, **kwargs)
    te = time.time()
    return te - ts
    
def num_queries(func=None, *args, **kwargs):
    from django.test.utils import CaptureQueriesContext
    from django.db import connections, DEFAULT_DB_ALIAS
    using = kwargs.pop("using", DEFAULT_DB_ALIAS)
    conn = connections[using]

    context = CaptureQueriesContext(conn)
    if func is None:
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
            
