import re


## 10.07
#def query_to_string(set, fld,  sep = " "):
#    flds = fld.split('.')
#    #: .order_by may return non-distinct results!
#    rslt_query = set.all().order_by(flds[0])
#    return sep.join([str(rec_getattr(q, flds)).zfill(2) for q in list(rslt_query)])
## 10.07
#def rec_getattr(obj, attrs):
#    if isinstance(attrs, list):
#        if len(attrs) == 1:
#            return getattr(obj, attrs[0])
#        else:
#            to_get = attrs[0]
#            try:
#                return rec_getattr(getattr(obj, to_get), attrs[1:])
#            except:
#                print("WOOPS", obj, type(obj))
#            else:
#                return ""
## 10.07                
#def join_fields(model, flds, exclude_m2m = True):
#    from django.db.models.fields.related import ManyToManyField
#    #flist = [fld.name for fld in model._meta.get_fields()[1:] if not exclude_m2m and not isinstance(fld, ManyToManyField)]
#    flist = model._meta.get_fields()
##    for fld in model._meta.get_fields()[1:]:
##        if isinstance(fld, ManyToManyField) and exclude_m2m: # : ForeignFields?!
##            continue
##        else:
##            flist.append(fld.name)
#    for tpl in flds:
#        flist[flist.index(tpl[0])] = (tpl[0], tpl[1])
#        flist.remove(tpl[1])
#    return flist
## 10.07    
#def get_main_fields(model,  as_str = True):
#    if as_str:
#        return [fld.attname for fld in model._meta.get_fields() if fld.concrete]
#    else:
#        return [fld for fld in model._meta.get_fields() if fld.concrete]
#        
## 25.07    
#def split_name(name):
#    kwds = [r'\bvan\b', r'\bvan.der\b', r'\bvan.de\b', r'\bde\b', r'\bvon\b',r'\bvan.den\b'
#            r'\bSt\.?', r'\bSaint\b', r'\bde.la\b', r'\bla\b'] 
#    jrsr = [r'\bJunior\b', r'\bJr\.?', r'\bSenior\b', r'\bSr\.?',  r'\bIII\.?', r'\bII\.?'] #r'\b.I.'
#    for w in kwds:
#        p = re.compile(w, re.IGNORECASE)
#        sep = re.search(p, name)
#        if sep:
#            
#            sep = sep.start()
#            v = name[:sep].strip()
#            n = name[sep:].strip()
#            return v, n
#    suffix = None
#    for w in jrsr:
#        p = re.compile(w, re.IGNORECASE)
#        sep = re.search(p, name)
#        if sep:
#            suffix = name[sep.start():sep.end()]
#            name = name[:sep.start()]+name[sep.end():]
#    v = " ".join(name.strip().split()[:-1]).strip()
#    n = name.strip().split()[-1]
#    if suffix:
#        n = n + " " + suffix
#    # NOTE: <3? Bisschen viel --- gibt ja schließlich viele Nachnamen mit <3 Buchstaben
#    if len(n)<3:
#        # ... and v: ? For if the nachname is just weird, but still a proper name (since it has a proper vorname, too)
#        if n.endswith('.') or len(n)==1:
#            # Bsp: Mark G. --> not a proper name
#            v = None
#            n = None
#    return v, n
#
    
##: put these two in a custom manager?
#def find_duplicates(qs, flds = []):
#    #: outdated. get_duplicates does this better
#    rslt = set()
#    model = qs.model
#    if not flds:#    
#def get_duplicates(qs, flds=[]):
#    from django.db import models
#    if isinstance(qs, models.base.ModelBase):
#        qs = qs.objects
#    if not flds:
#        if getattr(qs.model, 'dupe_fields'):
#            flds = getattr(qs.model, 'dupe_fields')
#        else:
#            flds = [fld.name for fld in qs.model._meta.fields if fld != qs.model._meta.pk]
#    
#    # Get all the model's fields + the explicit dupe fields.
#    qsmodelflds = set([fld.name for fld in qs.model._meta.fields])
#    qsmodelflds.update(flds)
#    
#    # Convert all queryset objects into dictionaries
#    val_dict = [i for i in qs.values(*qsmodelflds)]
#    
#    # ID-set of duplicates
#    ids = set()
#    
#    if len(flds)==1:
#        # get a flat list to avoid having to deal with one-item tuples
#        val_list = [i for i in qs.values_list(*flds, flat=True)]
#        for i in val_dict:
#            if val_list.count(i[flds[0]])>1:
#                if 'id' in i and i['id'] not in ids:
#                    ids.add(i['id'])
#                    yield i
#    else:
#        val_list = [i for i in qs.values_list(*flds, flat=False)]
#        for i in val_dict:
#            if val_list.count(tuple(i[fld] for fld in flds))>1:
#                if 'id' in i and i['id'] not in ids:        #  bei Ausgaben heißt das, dass num = 12 und lnum = 12 gleich sind...? oder rettet hier die reihenfolge der flds?
#                    ids.add(i['id'])
#                    yield i
#
#def get_duplicates2(qs, flds=[]):
#    if isinstance(qs, models.base.ModelBase):
#        qs = qs.objects
#    if not flds:
#        if getattr(qs.model, 'dupe_fields'):
#            flds = getattr(qs.model, 'dupe_fields')
#        else:
#            flds = [fld.name for fld in qs.model._meta.fields if fld != qs.model._meta.pk]
#    
#    # Get all the model's fields + the explicit dupe fields.
#    qsmodelflds = set([fld.name for fld in qs.model._meta.fields])
#    qsmodelflds.update(flds)
#    
#    # Convert all queryset objects into a list of dictionaries
#
#    
#    # ID-set of duplicates
#    duplicate_ids = set()
#    
#    val_list = []
#    
#    if len(flds)==1:
#        # get a flat list to avoid having to deal with one-item tuples
#        val_list = [i for i in qs.values_list(*flds, flat=True)]
#        for i in val_dict:
#            if val_list.count(i[flds[0]])>1:
#                if 'id' in i and i['id'] not in ids:
#                    ids.add(i['id'])
#                    yield i
#    else:
#        val_list = [i for i in qs.values_list(*flds, flat=False)]
#        for i in val_dict:
#            if val_list.count(tuple(i[fld] for fld in flds))>1:
#                if 'id' in i and i['id'] not in ids:        #  bei Ausgaben heißt das, dass num = 12 und lnum = 12 gleich sind...? oder rettet hier die reihenfolge der flds?
#                    ids.add(i['id'])
#                    yield i
#
#def generate_object_values(qs, flds, ids = None):
#    base_ids = ids or qs.values_list(qs.model._meta.pk.name, flat = True)               # all ids
#    for id in base_ids:
#        object_values = {'id':id}
#        object = qs.filter(pk=id)
#        for fld in flds:
#            values = [i for i in object.values_list(fld, flat = True)]
#            object_values[fld] = values
#        yield object_values

#        flds = [fld.name for fld in model._meta.fields if fld != model._meta.pk]
#    for i in qs.values(): 
#        if i[model._meta.pk.name] not in rslt:
#            val_noid = {k:v for k, v in i.items() if k in flds}
#            dupes = qs.filter(**val_noid).exclude(pk=i[model._meta.pk.name]) 
#            for d in dupes:
#                rslt.add(d.pk)
#    return rslt

    
#def delete_duplicates(model):
#    #: outdated. merge_duplicates does this better
#    for i in model.objects.all().values():
#        val_noid = {k:v for k, v in i.items() if k != model._meta.auto_field.name}
#        dupes = model.objects.filter(**val_noid).exclude(pk=i[model._meta.pk.name]).delete()
##    duplicates = find_duplicates(model)
##    if duplicates:
##        model.objects.filter(pk__in=duplicates).delete()
#
#def compactify(model, flds = [], stmt = ''):
#    #: outdated. merge_duplicates does this better
#    if not stmt:
#        if hasattr(model, 'compactify_stmt'):
#            stmt = getattr(model, 'compactify_stmt')
#    if not flds:
#        if hasattr(model, 'compactify_fields'):
#            flds = getattr(model, 'compactify_fields')
#        else:
#            flds = [fld.name for fld in model._meta.fields if fld != model._meta.pk]
#        
#    if stmt:
#        q = model.objects.raw(stmt)
#        ids = set([i.pk for i in q])
#    else:
#        ids = find_duplicates(model.objects, flds)
#    print("Compactify: {} Duplikate gefunden.".format(len(ids)))
#    
#    originals = set()
#    for id in ids:
#        record = model.objects.filter(pk=id)
#        if record.count()!=1:
#            continue
#            
#        record_valdict = {k:v for k, v in record.values()[0].items() if k in flds}
#        original = model.objects.exclude(pk__in=ids).filter(**record_valdict)
#        original_pk = original[0].pk
#        if not original_pk in originals:
#            duplicates = [i.pk for i in model.objects.exclude(pk=original_pk).filter(**record_valdict)]
#            print("original: ", model.objects.get(pk=original_pk), original_pk)
#            print("duplicates", duplicates)
#            for d in duplicates:
#                print(model.objects.get(pk=d), d)
#            print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
#            #model.merge(original_pk, *duplicates)
#            originals.add(original_pk)
#    return originals

## 25.07    
#def get_duplicates(qs, flds=[]):
#    from django.db import models
#    if isinstance(qs, models.base.ModelBase):
#        qs = qs.objects
#    if not flds:
#        if getattr(qs.model, 'dupe_fields'):
#            flds = getattr(qs.model, 'dupe_fields')
#        else:
#            flds = [fld.name for fld in qs.model._meta.fields if fld != qs.model._meta.pk]
#    
#    # Get all the model's fields + the explicit dupe fields.
#    qsmodelflds = set([fld.name for fld in qs.model._meta.fields])
#    qsmodelflds.update(flds)
#    
#    # Convert all queryset objects into dictionaries
#    val_dict = [i for i in qs.values(*qsmodelflds)]
#    
#    # ID-set of duplicates
#    ids = set()
#    
#    if len(flds)==1:
#        # get a flat list to avoid having to deal with one-item tuples
#        val_list = [i for i in qs.values_list(*flds, flat=True)]
#        for i in val_dict:
#            if val_list.count(i[flds[0]])>1:
#                if 'id' in i and i['id'] not in ids:
#                    ids.add(i['id'])
#                    yield i
#    else:
#        val_list = [i for i in qs.values_list(*flds, flat=False)]
#        for i in val_dict:
#            if val_list.count(tuple(i[fld] for fld in flds))>1:
#                if 'id' in i and i['id'] not in ids:        #  bei Ausgaben heißt das, dass num = 12 und lnum = 12 gleich sind...? oder rettet hier die reihenfolge der flds?
#                    ids.add(i['id'])
#                    yield i
#
#def get_duplicates2(qs, flds=[]):
#    if isinstance(qs, models.base.ModelBase):
#        qs = qs.objects
#    if not flds:
#        if getattr(qs.model, 'dupe_fields'):
#            flds = getattr(qs.model, 'dupe_fields')
#        else:
#            flds = [fld.name for fld in qs.model._meta.fields if fld != qs.model._meta.pk]
#    
#    # Get all the model's fields + the explicit dupe fields.
#    qsmodelflds = set([fld.name for fld in qs.model._meta.fields])
#    qsmodelflds.update(flds)
#    
#    # Convert all queryset objects into a list of dictionaries
#
#    
#    # ID-set of duplicates
#    duplicate_ids = set()
#    
#    val_list = []
#    
#    if len(flds)==1:
#        # get a flat list to avoid having to deal with one-item tuples
#        val_list = [i for i in qs.values_list(*flds, flat=True)]
#        for i in val_dict:
#            if val_list.count(i[flds[0]])>1:
#                if 'id' in i and i['id'] not in ids:
#                    ids.add(i['id'])
#                    yield i
#    else:
#        val_list = [i for i in qs.values_list(*flds, flat=False)]
#        for i in val_dict:
#            if val_list.count(tuple(i[fld] for fld in flds))>1:
#                if 'id' in i and i['id'] not in ids:        #  bei Ausgaben heißt das, dass num = 12 und lnum = 12 gleich sind...? oder rettet hier die reihenfolge der flds?
#                    ids.add(i['id'])
#                    yield i
#
#def generate_object_values(qs, flds, ids = None):
#    base_ids = ids or qs.values_list(qs.model._meta.pk.name, flat = True)               # all ids
#    for id in base_ids:
#        object_values = {'id':id}
#        object = qs.filter(pk=id)
#        for fld in flds:
#            values = [i for i in object.values_list(fld, flat = True)]
#            object_values[fld] = values
#        yield object_values
