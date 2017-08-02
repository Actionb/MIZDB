from django.db.utils import IntegrityError
from django.db.models import Aggregate
from django.utils.http import urlquote
from django.utils.html import format_html

from .models import *
from .constants import M2M_LIST_MAX_LEN
    
def concat_m2m(values, width = 50,  sep = ', ', z = 0):
    """ Concat and limit (to len width) values (from a m2m relation) """
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
    
def concat_limit(values, width = M2M_LIST_MAX_LEN, sep = ", ", z = 0):
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

def link_list(request, obj_list,  SEP = ", "):
    """ Returns a string with html links to the objects in obj_list separated by SEP.
        Used in ModelAdmin
    """
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

    
def merge(cls, original_pk, dupes, verbose=True):
    if not isinstance(dupes, list):
        dupes = [dupes]
        
    if len(dupes)<1:
        return
    
    # Cleanup dupe list
    ids = set([d.pk if isinstance(d, cls) else d for d in dupes])
    if isinstance(original_pk, cls):
        original_pk = original_pk.pk
    original = cls.objects.filter(pk=original_pk)
    if original.count()!=1:
        return
    o_valdict = original.values()[0]                
            
    for id in ids:
        record = cls.objects.filter(pk=id)
        if record.count()!=1:
            # something went very wrong
            print("WOOPS: id = ", id)
            continue
        if verbose:
            # TODO: remove duplicate fields in val_fields
            # TODO: print a nice a comparison of values
            val_fields = [fld.name for fld in cls._meta.fields] + getattr(cls, 'dupe_fields', [])
            print("\n"+"~"*20)
            print('Merging')
            print(original.values(*val_fields))
            print('with')
            print(record.values(*val_fields))
            inp = input("proceed? [y/n/q]: ")
            if inp == 'q':
                print("Aborting...")
                return False
            elif inp != 'y':
                continue
        
        # Expand original dict by values only found in duplicate, prefer original values if present
        for k, v in record.values()[0].items():
            # Duplicate has key that the original doesn't
            if k not in o_valdict.keys():
                o_valdict[k] = v
            # Duplicate has key that the original also has, but the original value is None
            elif k in o_valdict.keys() and not o_valdict[k]:
                o_valdict[k] = v
        # Update original queryset val dict
        try:
            original.update(**o_valdict)
        except Exception as e:
            print(e)
            raise e
            
        # Adjust values for related objects
        for rel in cls._meta.related_objects:
            # NOTE: zwischen m_to_o,o_to_m und m_to_m unterscheiden?
            # differentiate between ManyToManyField and ManyToXRelations
            if hasattr(rel, 'through'):
                # AAAAAAAAAAAAAAAHHHHHHHHHHHHHHHHH!!!!
                model = rel.through
                field = rel.field.m2m_reverse_field_name()
            else:
                model = rel.related_model
                field = rel.field.attname
            qs = model.objects.filter(**{field:id})
            if qs.exists():
                try:
                    qs.update(**{rel.field.attname:original_pk})
                except IntegrityError:
                    # TODO: account for UNIQUE CONSTRAINTS errors
                    continue
        try:
            record[0].delete()          # deleting via model delete()
        except Exception as e:
            print(e)
        
    return True
    
def print_tabular(to_print, columns = [], default_col_width=6):
    from itertools import chain
    if isinstance(to_print, dict):
        to_print = [to_print]
    if any(not isinstance(row, dict) for row in to_print):
        print("Printing requires an iterable of dicts.")
        raise
    
    column_ordering = columns[:] or list(set(chain(*[row.keys() for row in to_print])))
    # Allow column_ordering to consist of tuple/list with alias and key/name: (column_name,column_alias)
    for i, column in enumerate(column_ordering):
        if isinstance(column, tuple) and column[1]:
            continue
        else:
            column_ordering[i] = (column,column)
    
    # delete keys not existing in to_print.keys
    for key, alias in column_ordering:
        if any(key not in row.keys() for row in to_print):
            column_ordering.remove((key, alias))
    max_item_len = {}
    for row in to_print:
        for key, alias in column_ordering:
            try:
                len_v = len(str(row[key]))
            except:
                len_v = default_col_width
            max_item_len[key] = max(len_v, len(alias))+2
            
    header_string = ""
    for key, alias in column_ordering:
        header_string += "|" + alias.center(max_item_len[key]) + "|"
    print(header_string)
    print("="*len(header_string))
    for row in to_print:
        for key, alias in column_ordering:
            try:
                print("|"+str(row[key]).center(max_item_len[key])+"|", end="")
            except:
                print("column_ordering:", column_ordering)
                print("row.keys", row.keys())
        print()
    print()

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
    # NOTE: <3? Bisschen viel --- gibt ja schließlich viele Nachnamen mit <3 Buchstaben
    if len(n)<3:
        # ... and v: ? For if the nachname is just weird, but still a proper name (since it has a proper vorname, too)
        if n.endswith('.') or len(n)==1:
            # Bsp: Mark G. --> not a proper name
            v = None
            n = None
    return v, n

