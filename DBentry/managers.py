from collections import Counter, OrderedDict

from django.db import models, transaction
from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist, ValidationError

from DBentry.utils import flatten_dict
from DBentry.query import *

class MIZQuerySet(models.QuerySet):
    
    def find(self, q, **kwargs):
        """
        Finds any occurence of the search term 'q' in the queryset, depending on the search strategy used.
        """
        # Find the best strategy to use:
        #TODO: when searching in ausgabe, the ordering is all messed up
        if getattr(self.model, 'name_field', False):
            strat = ValuesDictSearchQuery
        elif getattr(self.model, 'primary_search_fields', False):
            strat = PrimaryFieldsSearchQuery
        else:
            strat = BaseSearchQuery
        result, exact_match = strat(self, **kwargs).search(q)
        return result
    
    def _duplicates(self, *fields, as_dict = False):
        if len(fields)==1:
            return self.single_field_dupes(*fields)
        else:
            return self.multi_field_dupes(*fields, as_dict = as_dict)
            
    def duplicates(self, *fields):
        dupes = self._duplicates(*fields)
        rslt = OrderedDict()
        for tpl in dupes:
            dupe_values, c = tpl[:-1], tpl[-1] #NOTE: this REQUIRES tuples/lists and does not work with dicts
            filter = dict(zip(fields, dupe_values))
            ids = self.filter(**filter).values_list('pk', flat=True)
            rslt[ids] = filter
        return rslt
        
    def exclude_empty(self, *fields):
        filter = {}
        for field_name in fields:
            try:
                field = self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                continue
            if field.null:
                filter[field_name+'__isnull'] = True
            if field.get_internal_type() in ('CharField', 'TextField'):
                filter[field_name] = ''
        return self.exclude(**filter)
        
    def single_field_dupes(self, field):
        count_name = field + '__count'
        return self.exclude_empty(field).values_list(field).annotate(**{count_name:models.Count(field)}).filter(**{count_name + '__gt':1}).order_by('-'+count_name)
        
    def multi_field_dupes(self, *fields, as_dict=False):
        #sorted(m1,key=lambda d: d[[k for k in d.keys() if '__count' in k][0]])
        #TODO: use values_dict? t = map(tuple,[d.values() for d in vd.values()]) -> s = [tuple(tuple(i) for i in l) for l in t]
        # vd(tuplfy =True) -> Counter(map(tuple,[d.values() for d in vd.values()]))
        # This would allow capturing multiple duplicate relations -- values_list only returns one item per relation!
        null_filter = {f + '__isnull':False for f in fields} #TODO: exclude empty string
        x = self.exclude_empty(*fields).values_list(*fields)
        rslt = []
        for tpl, c in Counter(x).items():
            if c>1:
                if as_dict:
                    d = dict(zip(fields, tpl))
                    d['__count'] = c
                    rslt.append(d)
                else:
                    rslt.append(tpl + (c, ))
        return rslt
        
    def values_dict(self, *flds, include_empty = False, flatten = False, tuplfy = False, **expressions):
        """
        An extension of QuerySet.values(). 
        
            For a pizza with two toppings and two sizes:
            values('pk', 'pizza__topping', 'pizza__size'): 
                    [ 
                        {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'Tiny'}, 
                        {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'Tiny'},
                        {'pk':1, 'pizza__topping': 'Onions', 'pizza__size': 'God'},
                        {'pk':1, 'pizza__topping': 'Bacon', 'pizza__size': 'God'},
                    ]
                    
            values_dict('pk','pizza__topping', 'pizza__size'):
                    {
                        '1' : {'pizza__topping' : ['Onions', 'Bacon' ], 'pizza__size': ['Tiny', 'God']},
                    }   
        """
        # pk_name is the variable that will refer to this query's primary key values.
        pk_name = self.model._meta.pk.name
        
        # Make sure the query includes the model's primary key values as we require it to build the result out of.
        # If flds is None, the query targets all the model's fields.
        if flds:
            if not pk_name in flds:
                if 'pk' in flds:
                    pk_name = 'pk'
                else:
                    flds = list(flds)
                    flds.append(pk_name)
                
        rslt = OrderedDict()
        for val_dict in self.values(*flds, **expressions):
            id = val_dict.pop(pk_name)
            if id in rslt:
                d = rslt.get(id)
            else:
                d = {}
                rslt[id] = d
            for k, v in val_dict.items(): 
                if not include_empty and v in [None, '', [], (), {}]:
                    continue
                if k not in d:
                    if tuplfy:
                        d[k] = (v, )
                    else:
                        d[k] = [v]
                elif v in d.get(k):
                    continue
                else:
                    if tuplfy:
                        d[k] += (v, )
                    else:
                        d.get(k).append(v)
        if flds and flatten:
            #TODO: flatten with flds empty (all fields requested)
            # Do not flatten fields that represent a reverse relation, as a list is expected
            exclude = []
            for field_path in flds:
                if field_path == 'pk':
                    continue
                field = get_fields_from_path(self.model, field_path)[0]
                if field.one_to_many or field.many_to_many:
                    exclude.append(field_path)
            return flatten_dict(rslt, exclude)
        return rslt
        
    def resultbased_ordering(self):
        return self
    
    def create_val_dict(self, key, value, tuplfy=True):
        qs = self
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
        
class CNQuerySet(MIZQuerySet):
    
    _updated = False
    
    def find(self, q, **kwargs):
        strat = ValuesDictSearchQuery(self, **kwargs)
        result, exact_match = strat.search(q)
        return result
    
    def bulk_create(self, objs, batch_size=None):
        # Set the _changed_flag on the objects to be created
        for obj in objs:
            obj._changed_flag = True
        return super().bulk_create(objs, batch_size)
        
    def defer(self, *fields):
        if '_name' not in fields:
            self._update_names()
        return super().defer(*fields)
        
    def filter(self, *args, **kwargs):
        if any(k.startswith('_name')  for k in kwargs):
            self._update_names()
        return super().filter(*args, **kwargs)
        
    @property
    def updated(self):
        """
        If the names haven't yet been updated, check if they *should* be updated.
        If _name is deferred OR _name is not in the fields to be loaded, do not attempt an update.
        Likewise if self._fields is not None and does not contain _name.
        """
        if not self._updated:
            # query.deferred_loading: 
            # A tuple that is a set of model field names and either True, if these
            # are the fields to defer, or False if these are the only fields to
            # load.
            deferred, fields_are_deferred = self.query.deferred_loading
            if fields_are_deferred:
                if '_name' not in deferred:
                    # We're good to try, _name was not defer()'ed
                    return False
            else:
                if '_name' in deferred:
                    # We're good to try, _name was only()'ed
                    return False
            if self._fields is not None and '_name' not in self._fields:
                # We haven't called values/values_list (with _name as a field)
                return False
            return True
        return self._updated
        
    def only(self, *fields):
        if '_name' in fields:
            self._update_names()
        return super().only(*fields)
    
    def update(self, **kwargs):
        # it is save to assume that a name update will be required after this update
        # if _changed_flag is not already part of the update, add it with the value True
        if '_changed_flag' not in kwargs:
           kwargs['_changed_flag'] = True
        return super().update(**kwargs)
    update.alters_data = True
    
    def values(self, *fields, **expressions):
        if '_name' in fields:
            self._update_names()
        return super().values(*fields, **expressions)
        
    def values_list(self, *fields, **kwargs):
        if '_name' in fields:
            self._update_names()
        return super().values_list(*fields, **kwargs)
                
    def _update_names(self):
        if self.query.can_filter() and self.filter(_changed_flag=True).exists():    
            with transaction.atomic():
                for pk, val_dict in self.filter(_changed_flag=True).values_dict(*self.model.name_composing_fields, flatten=True).items():
                    new_name = self.model._get_name(**val_dict)
                    self.filter(pk=pk).update(_name=new_name, _changed_flag=False)
        self._updated = True
    _update_names.alters_data = True

class AusgabeQuerySet(CNQuerySet):
            
    def filter(self, *args, **kwargs):
        # Overridden, to better deal with poorly formatted e_datum values
        # django's way of validating inputs for querysets is done via django.utils.dateparse.py
        if 'e_datum' in kwargs:
            try:
                return super(AusgabeQuerySet, self).filter(*args, **kwargs)
            except ValidationError:
                from datetime import datetime
                v = kwargs.get('e_datum', '')
                for possible_formatting in ["%d.%m.%Y", "%d.%m.%y","%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]: 
                    # See if the value given for e_datum fits any of the possible formats
                    try:
                        v = datetime.strptime(v, possible_formatting).date()
                    except ValueError:
                        continue
                    break
                # If we couldn't 'fix' the e_datum value, the queryset still contains the faulty value
                # and upon calling super, will raise an exception
                kwargs['e_datum'] = v
        return super(AusgabeQuerySet, self).filter(*args, **kwargs)
       
    def resultbased_ordering(self):
        if not self.query.where.children:
            # Only try to find a better ordering if we are not working on the entire ausgabe queryset 
            # (that is: if filtering has been done)
            return self
        from django.db.models import Min, Max
        self = self.annotate(
                jahr = Min('ausgabe_jahr__jahr'), 
                num = Min('ausgabe_num__num'), 
                lnum = Min('ausgabe_lnum__lnum'), 
                monat = Min('ausgabe_monat__monat_id'), 
                )
        temp = []
        from .models import magazin, ausgabe_num, ausgabe_lnum, ausgabe_monat
        for ausg_detail, detail_name in [(ausgabe_num, 'num'), (ausgabe_lnum, 'lnum')]:
            c = ausg_detail.objects.filter(ausgabe__in=self).values('ausgabe_id').distinct().count()
            temp.append((c, detail_name))
        temp.append(    (self.filter(e_datum__isnull=False).values('e_datum').count(), 'e_datum')   )
        temp.sort(reverse=True)
        ordering = [i[1] for i in temp]
        
        mag_ids = self.values_list('magazin_id', flat = True).distinct()
        if mag_ids.count()==1:
            merkmal = magazin.objects.get(pk=mag_ids.first()).ausgaben_merkmal
            if merkmal:
                if merkmal in ordering:
                    ordering.remove(merkmal)
                ordering.insert(0, merkmal)
         #NOTE: using these annotations caused an exception in BulkConfirmationView when updating its queryset
         # had to reset its order_by
         # maybe something isn't quite loading from inside a view?
        ordering = ['jahr'] + ordering + ['monat', 'sonderausgabe']
        return self.order_by(*ordering)
        
    def print_qs(self):
        qs = self
        flds = ['ausgabe_jahr__jahr', 'ausgabe_num__num', 'ausgabe_lnum__lnum', 'ausgabe_monat__monat']
        alias = ['Jahr','Nummer','lfd.Nummer','Monat']
        columns = list(zip(flds, alias))
        obj_values = qs.values_all(flds)
        for fld, alias in columns:
            if all(all(value is None for value in row[fld]) for row in obj_values):
                # Don't print columns whose rows are all None
                columns.remove((fld, alias))
        print_tabular(obj_values, columns)
        
    
    
class BuchQuerySet(MIZQuerySet):
    
    def filter(self, *args, **kwargs):
        from stdnum import isbn, ean    
        for k, v in kwargs.copy().items():
            if 'ISBN' in k and isbn.is_valid(v):
                # we only store formatted ISBN-13 
                kwargs[k] = isbn.format(v, convert = True)
            if 'EAN' in k and ean.is_valid(v):
                # we only store clean/compact/unformatted EAN
                kwargs[k] = ean.compact(v)
        return super().filter(*args, **kwargs)
