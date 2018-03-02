
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy

from django.db import models

"""
Search strategies:
"""

class BaseStrategy(object):
    
    _results = {}
    
    def __init__(self, queryset, search_fields = None, suffix = None, use_cache = False, pre_filter = True):
        self.search_fields = search_fields or queryset.model.get_search_fields()
        if isinstance(self.search_fields, str):
            self.search_fields = [self.search_fields]
        self.search_fields = list(self.search_fields) # 'cast' into a list
        self.pre_filter = pre_filter
        self._root_queryset = queryset
        self.ids_found = set()
        self.suffix = suffix or getattr(queryset.model, 'search_fields_suffixes')
        self.exact_match = False
        self.use_cache = use_cache
        if not self.use_cache:
            self._results = {}
    
    def get_queryset(self, q=None):
        if q and self.pre_filter:
            # Exclude any records that do not at least icontain q in any of the search_fields
            #NOTE: this *should* help, but I am not actually convinced that it does
            qobjects = models.Q()
            for search_field in self.search_fields:
                qobjects |= models.Q((search_field+'__icontains', q))
            return self._root_queryset.filter(qobjects).distinct()
        return self._root_queryset.all()
        
    def get_suffix(self, field, lookup=''):
        #TODO: fetch suffix from the model if possible
        if field + lookup in self.suffix:
            return self.suffix.get(field + lookup)
        elif field in self.suffix:
            return self.suffix.get(field)
        else:
            return None
    
    def append_suffix(self, instances, field, lookup=''):
        # Relying on model instance __str__ for the 'name' to append the suffix to
        suffix = self.get_suffix(field, lookup)
        
        if suffix:
            return [
                (o.pk, force_text(o) + " ({})".format(suffix)) for o in instances
            ]
        else:
            #TODO: return instances or (pk,__str__) tuples?
            return instances
            
    def _do_lookup(self, lookup, search_field, q):
        qs = self.get_queryset(q)
        rslt = []
        search_results = qs.exclude(pk__in=self.ids_found).filter(**{search_field + lookup:q})
        rslt.extend(self.append_suffix(search_results, search_field, lookup))
        self.ids_found.update(search_results.values_list('pk', flat=True))
        return rslt
        
    def exact_search(self, search_field, q):
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and bool(exact):
            self.exact_match = True
        return exact
        
    def startsw_search(self, search_field, q):
        return self._do_lookup('__istartswith', search_field, q)
        
    def contains_search(self, search_field, q=None):
        return self._do_lookup('__icontains', search_field, q)
        
    def search(self, q=None):
        if not q:
            return self._root_queryset, False
        q = str(q)
        
        if q in self._results and self.use_cache:
            print('Strategy: Fetching results from storage', len(self._results[q][0]), self.use_cache)
            return self._results[q]
            
        self.ids_found = set()
        self.exact_match = False
        rslt = self._search(q)
        if self.use_cache:
            self._results[q] = (rslt, self.exact_match)
        return rslt, self.exact_match
        
    def _search(self, q):
        """ Implements the actual search strategy. """
        rslt = []
        for search_field in self.search_fields:
            rslt.extend(self.exact_search(search_field, q) + self.startsw_search(search_field, q) + self.contains_search(search_field, q))
        return rslt

class PrimaryFieldsStrategy(BaseStrategy):
    """
    A search strategy that can separate 'useful' results from 'weak' results.
    """
    
    primary_search_fields = []
    weak_hits_sep = gettext_lazy('weak hits for "{q}"')
    separator_width = 36 # Select2 result box is 36 digits wide
    
    def __init__(self, queryset, *args, **kwargs):
        self.primary_search_fields = kwargs.pop('primary_search_fields', None) or getattr(queryset.model, 'primary_search_fields', None)
        super().__init__(queryset, *args, **kwargs)
        if not self.primary_search_fields:
            self.primary_search_fields = self.search_fields
        elif isinstance(self.primary_search_fields, str):
            self.primary_search_fields = [self.primary_search_fields]
        
        self.secondary_search_fields = [field for field in self.search_fields if field not in self.primary_search_fields]
    
    def get_separator(self, q, separator_text=None):
        """ Return a line to visually separate results from weak results. """
        separator_text = separator_text or force_text(self.weak_hits_sep)
        separator_text = " " + separator_text.format(q=q).strip() + " "
            
        return '{:-^{width}}'.format(separator_text, width = self.separator_width)
        
    def exact_search(self, search_field, q):
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and search_field in self.primary_search_fields and bool(exact):
            self.exact_match = True
        return exact
        
    def _search(self, q):
        #TODO: include 'startsw_search' in weak_hits for secondary_search_fields?
        rslt = []
        for search_field in self.primary_search_fields:
            rslt.extend(self.exact_search(search_field, q) + self.startsw_search(search_field, q) + self.contains_search(search_field, q))
        for search_field in self.secondary_search_fields:
            rslt.extend(self.exact_search(search_field, q) + self.startsw_search(search_field, q))
        
        #TODO: do not include the separator if there haven't been any results yet?
        weak_hits = [(0, self.get_separator(q))]
        for search_field in self.secondary_search_fields:
            weak_hits.extend(self.contains_search(search_field, q))
        if len(weak_hits)>1:
            rslt.extend(weak_hits)
        return rslt
        
        
class NameFieldStrategy(PrimaryFieldsStrategy):
    
    name_field = None
    
    def __init__(self, queryset, *args, **kwargs):
        self.name_field = kwargs.pop('name_field', None) or getattr(queryset.model, 'name_field', None)
        super().__init__(queryset, *args, **kwargs)
        if not self.name_field:
            # If no name_field could be found, take the first field of either primary or secondary_search_fields
            if self.primary_search_fields:
                self.name_field = self.primary_search_fields[0]
            else:
                self.name_field = self.secondary_search_fields[0]
        self._root_queryset = self._root_queryset.values_list('pk', self.name_field)
    
    def append_suffix(self, tuple_list, field, lookup=''):
        suffix = self.get_suffix(field, lookup)
        
        if suffix:
            return [
                (pk, name + " ({})".format(suffix)) for pk, name in tuple_list
            ]
        else:
            return tuple_list
    
class ValuesDictStrategy(NameFieldStrategy):
    
    def append_suffix(self, pk, name, field, lookup=''):
        suffix = self.get_suffix(field, lookup)
        
        if suffix:
            return [(pk, name + " ({})".format(suffix))]
        else:
            return [(pk, name)]
        
    def _do_lookup(self, lookup, search_field, q):
        # values_dict is a dict of dicts of lists! {pk: {field:[values,...] ,...},... }
        rslt = []
        
        def lookup_values(search_field):
            ids = set()
            rslts = []
            
            for pk, data_dict in self.values_dict.copy().items():
                values_list = data_dict.get(search_field, None)
                if values_list:
                    match = False
                    if lookup == '__iexact':
                        if any(str(s) == q for s in values_list):
                            match = True
                    elif lookup == '__istartswith':
                        if any(str(s).startswith(q) for s in values_list):
                            match = True
                    else:
                        if any(q.casefold() in str(s).casefold() for s in values_list):
                            match = True
                    if match:
                        rslt.extend(self.append_suffix(pk, data_dict.get(self.name_field)[0], search_field, lookup))
                        ids.add(pk)
                        self.values_dict.pop(pk)
            return ids, rslts
        
        ids_found, rslts = lookup_values(search_field)
        rslt.extend(rslts)
        self.ids_found.update(ids_found)
        return rslt
        
    def search(self, q=None):
        if q:
            q = str(q)
            self.values_dict = self.get_queryset(q).values_dict(*self.search_fields)
        return super().search(q)
        
def a():
    from DBentry.models import ausgabe, tmag
    primary = ['_name']
    suffix = {
        'ausgabe_monat__monat__monat':'Monat', 
        'sonderausgabe':'Sonderausgabe', 
        'ausgabe_lnum__lnum':'Lnum', 
        'e_datum':'E.datum', 
        'status':'Status', 
        'ausgabe_num__num':'Num', 
        'jahrgang':'Jahrgang', 
        'ausgabe_monat__monat__abk':'Monat Abk.', 
        'ausgabe_jahr__jahr' : 'Jahr'
        }
    return ValuesDictStrategy(tmag.ausgabe_set.all(), primary_search_fields=primary, suffix=suffix)
    
def b():
    from DBentry.models import genre
    search_fields = ['genre', 'obergenre__genre', 'genre_alias__alias']
    suffix = {'obergenre__genre':'Ober', 'genre_alias__alias':'Genre-Alias'}
    return ValuesDictStrategy(genre.objects, search_fields=search_fields, suffix=suffix)
        
def get_vdstrat():
    from DBentry.models import band
    primary = ['band_name', 'band_alias__alias']
    suffix = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied', 'musiker__musiker_alias__alias':'Mitglied-Alias'}
    strat = ValuesDictStrategy(band.objects, name_field='band_name', primary_search_fields = primary, use_cache=False)
    strat.suffix = suffix
    return strat

def get_strat():
    from DBentry.models import band
    primary = ['band_name', 'band_alias__alias']
    suffix = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied', 'musiker__musiker_alias__alias':'Mitglied-Alias'}
    strat = NameFieldStrategy(band.objects, name_field='band_name', primary_search_fields = primary, use_cache=False)
    strat.suffix = suffix
    return strat
