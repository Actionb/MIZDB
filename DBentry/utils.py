import re
from functools import partial

from django.db import transaction
from django.db.utils import IntegrityError
from django.db.models import Aggregate

from django.utils.http import urlquote
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.text import capfirst

from django.urls import reverse, NoReverseMatch

from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename

from .constants import M2M_LIST_MAX_LEN

def merge_records(original, qs, update_data = None, expand_original = True):
    """ Merges original object with all other objects in qs and updates original's values with those in update_data. 
        Returns the updated original.
    """
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
                for i in related_qs:
                    try:
                        with transaction.atomic():
                            getattr(original, rel.get_accessor_name()).add(i)
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations
                        pass
        qs.delete()
    return original_qs.first(), update_data
    
def concat_limit(values, width = M2M_LIST_MAX_LEN, sep = ", ", z = 0):
    """
        Joins string values of iterable 'values' up to a length of 'width'.
    """
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

def link_list(request, obj_list,  SEP = ", ", path = None):
    """ Returns a string with html links to the objects in obj_list separated by SEP.
        Used in ModelAdmin
    """
    obj_list_strings = []
    for obj in obj_list:
        if path:
            obj_path = reverse(path, args = [obj.pk])
        else:
            obj_path = request.path + str(obj.pk)
        obj_list_strings.append(format_html('<a href="{}">{}</a>', urlquote(obj_path), force_text(obj)))
    return format_html(SEP.join(obj_list_strings))
    try:
        obj_list_string = SEP.join([
                    format_html('<a href="{}">{}</a>',
                    urlquote(request.path+str(obj.pk)), 
                    force_text(obj))
                    for obj in obj_list
                    ])
    except:
        print("WARNING : Failed to create link_list.")
        return SEP.join([force_text(obj) for obj in obj_list])
    return format_html(obj_list_string)
#    def format_callback(obj):
#        has_admin = obj.__class__ in admin_site._registry
#        opts = obj._meta
#
#        no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
#                                   force_text(obj))
#
#        if has_admin:
#            try:
#                admin_url = reverse('%s:%s_%s_change'
#                                    % (admin_site.name,
#                                       opts.app_label,
#                                       opts.model_name),
#                                    None, (quote(obj._get_pk_val()),))
#            except NoReverseMatch:
#                # Change url doesn't exist -- don't display link to edit
#                return no_edit_link
    
def model_from_string(model_name):
    from django.apps import apps 
    try:
        return apps.get_model('DBentry', model_name)
    except LookupError:
        return None

def swap_dict(d):
    rslt = {}
    for k, v in d.items():
        try:
            rslt[v] = k
        except TypeError:
            rslt[tuple(v)] = k
    return rslt

def create_val_dict(qs, key, value, tuplfy=True):
    dict_by_key = {}
    dict_by_val = {}
    for k, v in qs.values_list(key, value):
        try:
            dict_by_key[k].add(v)
        except:
            dict_by_key[k] = set()
            dict_by_key[k].add(v)
        if not tuplfy:
            try:
                dict_by_val[v].add(k)
            except:
                dict_by_val[v] = set()
                dict_by_val[v].add(k)
    if tuplfy:
        for k, v in dict_by_key.items():
            v = tuple(v)
            dict_by_key[k] = v
            try:
                dict_by_val[v].add(k)
            except:
                dict_by_val[v] = set()
                dict_by_val[v].add(k)
    return dict_by_key, dict_by_val

class Concat(Aggregate):
    # supports COUNT(distinct field)
    function = 'GROUP_CONCAT'
    template = '%(function)s(%(distinct)s%(expressions)s)'

    def __init__(self, expression, distinct=False, **extra):
        super(Concat, self).__init__(
            expression,
            distinct='DISTINCT ' if distinct else '',
            output_field=models.CharField(),
            **extra)

    
def split_name(name):
    """ Splits a full name into pre- and surname while accounting for certain name-specific keywords like 'von' or 'van de'
        or 'Senior', etc.
    """
    kwds = [r'\bvan\b', r'\bvan.der\b', r'\bvan.de\b', r'\bde\b', r'\bvon\b',r'\bvan.den\b'
            r'\bSt\.?', r'\bSaint\b', r'\bde.la\b', r'\bla\b'] 
    jrsr = [r'\bJunior\b', r'\bJr\.?', r'\bSenior\b', r'\bSr\.?',  r'\bIII\.?', r'\bII\.?'] #r'\b.I.'
    for w in kwds:
        p = re.compile(w, re.IGNORECASE)
        sep = re.search(p, name)
        if sep:
            
            sep = sep.start()
            v = name[:sep].strip()
            n = name[sep:].strip()
            return v, n
    suffix = None
    for w in jrsr:
        p = re.compile(w, re.IGNORECASE)
        sep = re.search(p, name)
        if sep:
            suffix = name[sep.start():sep.end()]
            name = name[:sep.start()]+name[sep.end():]
    v = " ".join(name.strip().split()[:-1]).strip()
    n = name.strip().split()[-1]
    if suffix:
        n = n + " " + suffix
    if len(n)<3:
        # ... and v: ? For if the nachname is just weird, but still a proper name (since it has a proper vorname, too)
        if n.endswith('.') or len(n)==1:
            # Bsp: Mark G. --> not a proper name
            v = None
            n = None
    return v, n

def dict_to_tuple(d):
    return tuple((k, v) for k, v in d.items())
    
def tuple_to_dict(t):
    return {k:v for k, v in t}

def multisplit(values, seperators = []):
    """Splits a string at each occurence of s in seperators."""
    if len(seperators)==1:
        return [i.strip() for i in values.split(seperators[0])]
    rslt = []
    last_sep = 0
    for index, c in enumerate(values):
        if c in seperators:
            rslt.append(values[last_sep:index].strip())
            last_sep = index+1
    rslt.append(values[last_sep:].strip())
    return rslt
    
def split_field(field_name, data, seperators = [',']):
    """ Splits the content of data[field_name] according to seperators and merges the new values back into a list of dicts."""
    if not data.get(field_name):
        return [data]
    rslt = []
    data_rest = {k:v for k, v in data.items() if k != field_name}
    for d in set(recmultisplit(data.get(field_name, ''), seperators)):
        x = data_rest.copy()
        x.update({field_name:d})
        rslt.append(x)
    return rslt
    

def recmultisplit(values, seperators = []):
    """Splits a string at each occurence of s in seperators."""
    if len(seperators)==1:
        return [i.strip() for i in values.split(seperators[0])]
    rslt = []
    seps = seperators[:]
    sep = seps.pop()
    
    for x in values.split(sep):
        rslt += recmultisplit(x, seps)
    return rslt    

def instance_to_dict():    
    pass
    
def print_list(a_list, file=None):
    printf = partial(print, file=file)
    for i in a_list:
        printf(i)
        
def print_dict(a_dict, file=None):
    printf = partial(print, file=file)
    for k, v in a_dict.items():
        printf(str(k)+":")
        printf(v)
        printf("~"*20)
        
def get_obj_link(obj, opts, user, admin_site):
    
    no_edit_link = '%s: %s' % (capfirst(opts.verbose_name),
                               force_text(obj))

    try:
        admin_url = reverse('%s:%s_%s_change'
                            % (admin_site.name,
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
    return format_html('{}: <a href="{}">{}</a>',
                       capfirst(opts.verbose_name),
                       admin_url,
                       obj)
    
