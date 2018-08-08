from collections import Counter, OrderedDict
from itertools import chain

from django.db import models, transaction
from django.db.models import Count, Sum, Min, Max
from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist

from DBentry.utils import flatten_dict
from DBentry.query import *


class MIZQuerySet(models.QuerySet):
    
    def find(self, q, ordered = False, **kwargs):
        """
        Finds any occurence of the search term 'q' in the queryset, depending on the search strategy used.
        """
        # Find the best strategy to use:
        if getattr(self.model, 'name_field', False):
            strat_class = ValuesDictSearchQuery
        elif getattr(self.model, 'primary_search_fields', False):
            strat_class = PrimaryFieldsSearchQuery
        else:
            strat_class = BaseSearchQuery
        strat = strat_class(self, **kwargs)
        result, exact_match = strat.search(q)
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
        for val_dict in list(self.values(*flds, **expressions)): # NOTE: self.values() can mess with the ordering!?
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
        if flatten:
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
        #TODO: was this ever finished?
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
    
    def find(self, q, ordered = True, **kwargs):
        strat = ValuesDictSearchQuery(self.all(), **kwargs)
        result, exact_match = strat.search(q)
        if result and ordered and self.ordered:
            # Restore order that was messed up by the search
            ordered_result = []
            for id in self.values_list('pk', flat = True):
                if id in strat.ids_found:
                    for tpl in result:
                        if tpl[0] == id:
                            ordered_result.append(tpl)
            return ordered_result
        return result
        
    def data_dump(self, fields = None):
        if fields is None:
            fields = [
                'magazin__magazin_name', 'sonderausgabe', 'jahrgang', 'e_datum', 
                'ausgabe_jahr__jahr', 'ausgabe_lnum__lnum', 'ausgabe_num__num', 'ausgabe_monat__monat__ordinal', 
            ]
        vd = self.values_dict(*fields, flatten = True)
        rslt = []
        for pk, val_dict in vd.items():
            y = val_dict.copy()
            x = OrderedDict()
            x['pk'] = pk
            for f in fields:
                if f in y:
                    x[f] = y[f]
            rslt.append(x)
        return rslt
    
    def chronologic_order(self, ordering = None):
        if not self.exists() or not self.query.where.children:
            # Don't bother if queryset is empty or not filtered in any way
            return self.order_by('pk') # django would warn about an unordered list even if it was empty
            
        default_ordering = ['magazin', 'jahr', 'jahrgang', 'sonderausgabe']
        if ordering is None:
            ordering = default_ordering
            pk_order_item = 'pk'
        else:
            if 'pk' in ordering:
                pk_order_item = ordering.pop(ordering.index('pk'))
            elif '-pk' in ordering:
                pk_order_item = ordering.pop(ordering.index('-pk'))
            else:
                pk_order_item = 'pk'
                
            # Remove any leading '-' so we do not append 'magazin' to ['-magazin']
            stripped_ordering = [i[1:] if i[0] == '-' else i for i in ordering]
            for o in default_ordering:
                if o not in stripped_ordering:
                    ordering.append(o) #NOTE: just append?
                
        # Determine if jahr should come before jahrgang in ordering
        jj_values = list(self.values_list('ausgabe_jahr', 'jahrgang'))
        # Remove empty values and unzip the 2-tuples into two lists
        jahr_values, jahrgang_values = (list(filter(lambda x:x is not None, l)) for l in zip(*jj_values))
        if len(jahrgang_values) > len(jahr_values):
            # prefer jahrgang over jahr 
            jahr_index = ordering.index('jahr')
            jahrgang_index = ordering.index('jahrgang')
            ordering[jahr_index] = 'jahrgang'
            ordering[jahrgang_index] = 'jahr'
        
        # Find the best criteria to order with, which might be either: num, lnum, monat or e_datum
        # Count the presence of the different criteria and sort them accordingly.
        # Account for the joins by taking each sum individually.
        # Since sorted() is stable, we can set the default order to (lnum, monat, num) in case any sum values are equal.
        counted = OrderedDict(chain( 
            self.annotate(c = Count('ausgabe_num')).aggregate(num__sum = Sum('c')).items(), 
            self.annotate(c = Count('ausgabe_monat')).aggregate(monat__sum = Sum('c')).items(),
            self.annotate(c = Count('ausgabe_lnum')).aggregate(lnum__sum = Sum('c')).items(), 
            self.annotate(c = Count('e_datum')).aggregate(e_datum__sum = Sum('c')).items(), 
        ))
        criteria = sorted(counted.items(), key = lambda itemtpl: itemtpl[1], reverse = True)
        result_ordering = [sum_name.split('__')[0] for sum_name, sum in criteria]
        ordering.extend(result_ordering + [pk_order_item])
        
        self = self.annotate(
            num = Max('ausgabe_num__num'), 
            monat = Max('ausgabe_monat__monat__ordinal'),
            lnum = Max('ausgabe_lnum__lnum'),  
            jahr = Min('ausgabe_jahr__jahr'), 
        ).order_by(*ordering)
        return self
        
class BuchQuerySet(MIZQuerySet):
    
    def filter(self, *args, **kwargs):
        from stdnum import isbn, ean    
        for k, v in kwargs.copy().items():
            if 'ISBN' in k and isbn.is_valid(v):
                # we only store formatted ISBN-13 
                kwargs[k] = isbn.format(v, convert = True)
            if 'EAN' in k and ean.is_valid(v):
                # we only store clean/compact/unformatted EAN (without any dashes)
                kwargs[k] = ean.compact(v)
        return super().filter(*args, **kwargs)
