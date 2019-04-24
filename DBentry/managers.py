from collections import Counter, OrderedDict
from itertools import chain
        
from django.db import models, transaction
from django.db.models import Count, Sum, Min, Max
from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist

from DBentry.utils import flatten_dict, leapdays, build_date
from DBentry.query import BaseSearchQuery, ValuesDictSearchQuery, PrimaryFieldsSearchQuery

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
        
    def qs_dupes(self, *fields):
        annotations, filters, ordering = {}, {}, []
        for field in fields:
            count_name = field + '__count'
            annotations[count_name] = models.Count(field)
            filters[count_name + '__gt'] = 1
            ordering.append('-' + count_name)
        return self.values(*fields).annotate(**annotations).filter(**filters).order_by(*ordering)
        
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
        for val_dict in list(self.values(*flds, **expressions)):
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
        
class CNQuerySet(MIZQuerySet):
    
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
                    self.order_by().filter(pk=pk).update(_name=new_name, _changed_flag=False)
    _update_names.alters_data = True

class AusgabeQuerySet(CNQuerySet):
    
    chronologically_ordered = False
     
    def _chain(self, **kwargs):
        # QuerySet._chain() will update the clone's __dict__ with the kwargs we give it. (in django1.11: QuerySet._clone() did this job)
        if 'chronologically_ordered' not in kwargs:
            kwargs['chronologically_ordered'] = self.chronologically_ordered
        return super()._chain(**kwargs)        
        
    def order_by(self, *args, **kwargs):
        # Any call to order_by is almost guaranteed to break the chronologic ordering.
        self.chronologically_ordered = False
        return super().order_by(*args, **kwargs)
    
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
        
    def increment_jahrgang(self, start_obj, start_jg = 1):
        start = start_obj or self.chronologic_order().first()
        start_date = start.e_datum
        years = start.ausgabe_jahr_set.values_list('jahr', flat = True)
        if start_date:
            start_year = start_date.year
        elif years:
            start_year = min(years)
        else:
            start_year = None
            
        ids_seen = {start.pk}
        update_dict = {start_jg : [start.pk]}
        queryset = self.exclude(pk = start.pk)
        
        # Increment by date
        if start_date is None:
            month_ordinals = start.ausgabe_monat_set.values_list('monat__ordinal', flat = True)
            start_date = build_date(years, month_ordinals)
            
        if start_date:
            val_dicts = queryset.values_dict('e_datum', 'ausgabe_jahr__jahr', 'ausgabe_monat__monat__ordinal', include_empty = False, flatten = False)
            for pk, val_dict in val_dicts.items():
                if 'e_datum' in val_dict:
                   obj_date = val_dict.get('e_datum')[-1]
                elif not ('ausgabe_jahr__jahr' in val_dict and 'ausgabe_monat__monat__ordinal' in val_dict):
                    continue
                else:
                    obj_date = build_date(
                        val_dict['ausgabe_jahr__jahr'], val_dict['ausgabe_monat__monat__ordinal']
                    )
                if obj_date < start_date:
                    # If the obj_date lies before start_date the obj_jg will always be start_jg - 1
                    # plus the year difference between the two dates.
                    # If the days and month of each date match, obj_date marks the BEGINNING of the obj_jg, 
                    # thus we need to handle it inclusively (subtracting 1 from the day difference, thereby requiring 366 days difference)
                    obj_jg = start_jg - (1 +\
                        int(((start_date - obj_date).days - leapdays(start_date, obj_date) - 1)/365))
                else:
                    obj_jg = start_jg + \
                        int(((obj_date - start_date).days - leapdays(start_date, obj_date))/365)
                if obj_jg not in update_dict:
                    update_dict[obj_jg] = []
                update_dict[obj_jg].append(pk)
                ids_seen.add(pk)
        
        # Increment by num
        nums = start.ausgabe_num_set.values_list('num', flat = True)
        if nums and start_year:
            queryset = queryset.exclude(pk__in = ids_seen)
            start_num = min(nums)
            
            val_dicts = queryset.values_dict('ausgabe_num__num', 'ausgabe_jahr__jahr', include_empty = False, flatten = False)
            for pk, val_dict in val_dicts.items():
                if 'ausgabe_num__num' not in val_dict or 'ausgabe_jahr__jahr' not in val_dict:
                    continue
                    
                obj_year = min(val_dict['ausgabe_jahr__jahr'])
                obj_num = min(val_dict['ausgabe_num__num'])
                if len(val_dict['ausgabe_jahr__jahr']) > 1:
                    # The ausgabe spans two years, choose the highest num number to order it at the end of the year
                    obj_num = max(val_dict['ausgabe_num__num'])
                
                if (obj_num > start_num and obj_year == start_year) or\
                    (obj_num < start_num and obj_year == start_year + 1):
                    update_dict[start_jg].append(pk)
                else:
                    obj_jg = start_jg + obj_year - start_year
                    if obj_num < start_num:
                        # the object was released in the 'previous' jahrgang 
                        obj_jg -= 1
                    if obj_jg not in update_dict:
                        update_dict[obj_jg] = []
                    update_dict[obj_jg].append(pk)
                ids_seen.add(pk)
    
        # Increment by year
        if start_year:
            queryset = queryset.exclude(pk__in = ids_seen)
            
            for pk, val_dict in queryset.values_dict('ausgabe_jahr__jahr', include_empty = False, flatten = False).items():
                if 'ausgabe_jahr__jahr' not in val_dict:
                    continue
                obj_jg = start_jg + min(val_dict['ausgabe_jahr__jahr']) - start_year
                if obj_jg not in update_dict:
                    update_dict[obj_jg] = []
                update_dict[obj_jg].append(pk)
                ids_seen.add(pk)
        
            
        with transaction.atomic():
            for jg, ids in update_dict.items():
                self.filter(pk__in=ids).update(jahrgang=jg)
        
        return update_dict

    #TODO: rename chronologic_order to chronological_order ??
    def chronologic_order(self, ordering = None):
        """
        Returns this queryset chronologically ordered if it is filtered to a single magazin.
        """
        if self.chronologically_ordered:
            return self
            
        # A chronologic order is (mostly) consistent ONLY within the ausgabe_set of one particular magazin.
        # Meaning if the queryset contains the ausgaben of more than one magazin, we may end up replacing one
        # 'poor' ordering (the default one) with another poor chronologic one.
        
        # The if condition could also be:
        #   if self.model._meta.get_field('magazin') not in [child.lhs.target for child in self.query.where.children]
        # Which would not hit the database.
        # But I am not sure if lhs.target really specifies the field that was filtered on.
        if self.only('magazin').distinct().values_list('magazin').count() != 1:
            # This condition is also True if self is an empty queryset.
            if ordering is not None:
                return self.order_by(*ordering)
            return self.order_by(*self.model._meta.ordering)
        
        default_ordering = ['magazin', 'jahr', 'jahrgang', 'sonderausgabe']
        if ordering is None:
            ordering = default_ordering
        else:
            ordering.extend(default_ordering)
            
        pk_name = self.model._meta.pk.name
        # Retrieve the first item in ordering that refers to the primary key, so we can later append 
        # it to the final ordering.
        # It makes no sense to have the queryset be ordered primarily on the primary key.
        try:
            pk_order_item = next(filter(lambda i: i in ('pk', '-pk', pk_name, '-' + pk_name), ordering))
            ordering.remove(pk_order_item)
        except StopIteration:
            # No primary key in ordering, use '-pk' as default.
            pk_order_item = '-pk'
                
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
        # NOTE: tests succeed with or without distinct = True
        counted = self.aggregate(
            num__sum = Count('ausgabe_num', distinct = True), 
            monat__sum = Count('ausgabe_monat', distinct = True), 
            lnum__sum = Count('ausgabe_lnum', distinct = True), 
            e_datum__sum = Count('e_datum', distinct = True), 
        )
        #TODO: this should be the default (due to chronologic accuracy):
        default_criteria_ordering = ['e_datum__sum', 'lnum__sum', 'monat__sum', 'num__sum']
        default_criteria_ordering = ['num__sum', 'monat__sum', 'lnum__sum', 'e_datum__sum']
        
        # Tuples are sorted lexicographically in ascending order: if any item of two tuples is the same, it goes on to the next item:
        # sorted([(1, 'c'), (1, 'b'), (2, 'a')]) = [(1,'b'), (1, 'c'), (2, 'a')]
        # In this case, we want to order the sums (tpl[1]) in descending, i.e. reverse, order (hence the minus operand)
        # and if any sums are equal, the order of sum_names in the defaults decides.
        criteria = sorted(
            counted.items(), 
            key = lambda itemtpl: (-itemtpl[1], default_criteria_ordering.index(itemtpl[0]))
        )
        result_ordering = [sum_name.split('__')[0] for sum_name, sum in criteria]
        ordering.extend(result_ordering + [pk_order_item])
        
        clone = self.annotate(
            num = Max('ausgabe_num__num'), 
            monat = Max('ausgabe_monat__monat__ordinal'),
            lnum = Max('ausgabe_lnum__lnum'),  
            jahr = Min('ausgabe_jahr__jahr'), 
        ).order_by(*ordering)
        clone.chronologically_ordered = True
        return clone
        
