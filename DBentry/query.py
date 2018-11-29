
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy
from django.core.exceptions import FieldDoesNotExist
from django.contrib.admin.utils import get_fields_from_path

from django.db import models

#TODO: this does not check/catch if a lookup expression is allowed
    
class BaseSearchQuery(object):
    """
    The basic search strategy. Search by exactness by search_field. 
    """
    
    _results = {}
    
    def __init__(self, queryset, search_fields = None, suffix = None, use_suffix = True, **kwargs):
        self.search_fields = search_fields or queryset.model.get_search_fields()
        if isinstance(self.search_fields, str):
            self.search_fields = [self.search_fields]
        self.search_fields = list(self.search_fields) # 'cast' into a list
        self._root_queryset = queryset
        self.ids_found = set()
        self.suffix = suffix or getattr(queryset.model, 'search_fields_suffixes', {})
        self.use_suffix = use_suffix
        self.exact_match = False
        
    def get_model_field(self, field_name):
        try:
            return get_fields_from_path(self._root_queryset.model, field_name)[-1]
        except FieldDoesNotExist:
            return None

    def clean_string(self, s, field_name):
        s = str(s).strip().casefold()
        if isinstance(self.get_model_field(field_name), models.DateField):
            # django.models.DateField expects a string of format 'yyyy-mm-dd' 
            # __i<lookup_name> lookups work fine with a partial string of format 'yyyy-mm-dd'
            # try transforming a string of format 'dd.mm.yyyy'
            if '.' in s:
                s = "-".join(date_bit.zfill(2) for date_bit in reversed(s.split('.')))
        return s
        
    def get_queryset(self, q=None):
        return self._root_queryset.all()
        
    def get_suffix(self, field, lookup=''):
        if field + lookup in self.suffix:
            return self.suffix.get(field + lookup)
        elif field in self.suffix:
            return self.suffix.get(field)
        else:
            return ""
    
    def append_suffix(self, instances, field, lookup=''):
        # Relying on model instance __str__ for the 'name' to append the suffix to
        suffix = self.get_suffix(field, lookup)
        
        if self.use_suffix and suffix:
            suffix = " ({})".format(suffix)
        return [
                (o.pk, force_text(o) + suffix) for o in instances
            ]
            
    def _do_lookup(self, lookup, search_field, q):
        q = self.clean_string(q, search_field)
        qs = self.get_queryset()
        rslt = []
        search_results = qs.exclude(pk__in=self.ids_found).filter(**{search_field + lookup:q})
        new_rslts = self.append_suffix(search_results, search_field, lookup)
        self.ids_found.update([pk for pk, name in new_rslts])
        rslt.extend(new_rslts)
        return rslt
        
    def exact_search(self, search_field, q):
        #q = self.clean_string(q)
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and bool(exact):
            self.exact_match = True
        return exact
        
    def startsw_search(self, search_field, q):
        #q = self.clean_string(q)
        return self._do_lookup('__istartswith', search_field, q)
        
    def contains_search(self, search_field, q=None):
        #q = self.clean_string(q)
        return self._do_lookup('__icontains', search_field, q)
        
    def search(self, q):
        if not q:
            return self._root_queryset, False
            
        self.ids_found = set()
        self.exact_match = False
        rslt = self._search(q)
        return rslt, self.exact_match
        
    def _search(self, q):
        """ Implements the actual search strategy. """
        rslt = []
        for search_field in self.search_fields:
            rslt.extend(self.exact_search(search_field, q) + self.startsw_search(search_field, q) + self.contains_search(search_field, q))
        return rslt

class PrimaryFieldsSearchQuery(BaseSearchQuery):
    """
    A search strategy that can separate 'useful' results from 'weak' results.
    """
    
    primary_search_fields = []
    weak_hits_sep = gettext_lazy('weak hits for "{q}"')
    separator_width = 36 # Select2 result box is 36 digits wide
    
    def __init__(self, queryset, use_separator = True, *args, **kwargs):
        self.use_separator = use_separator
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
        #q = self.clean_string(q)
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and search_field in self.primary_search_fields and bool(exact):
            self.exact_match = True
        return exact
        
    def _search(self, q):
        rslt = []
        for search_field in self.primary_search_fields:
            rslt.extend(self.exact_search(search_field, q) + self.startsw_search(search_field, q) + self.contains_search(search_field, q))
        for search_field in self.secondary_search_fields:
            rslt.extend(self.exact_search(search_field, q))
        
        weak_hits = []
        for search_field in self.secondary_search_fields:
            weak_hits.extend(self.startsw_search(search_field, q) + self.contains_search(search_field, q))
        if weak_hits:
            if self.use_separator and len(rslt):
                weak_hits.insert(0, (0, self.get_separator(q)))
            rslt.extend(weak_hits)
        return rslt
        
        
class NameFieldSearchQuery(PrimaryFieldsSearchQuery):
    """
    Limits the possible results to the values of the respective name_field.
    """
    
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
        
        if self.use_suffix and suffix:
            suffix = " ({})".format(suffix)
        return [
            (pk, name + suffix) for pk, name in tuple_list
        ]
    
class ValuesDictSearchQuery(NameFieldSearchQuery):
    """
    Fetch all the relevant data first and then do a search in memory.
    """
    
    def get_queryset(self, q):
        # To limit the length of values_dict, exclude any records that do not at least icontain q in any of the search_fields
        qobjects = models.Q()
        for search_field in self.search_fields:
            for i in q.split():
                qobjects |= models.Q((search_field+'__icontains', self.clean_string(i, search_field)))
        return self._root_queryset.filter(qobjects)
        
    def _do_lookup(self, lookup, search_field, q):
        # values_dict is a dict of dicts of lists! {pk: {field:[values,...] ,...},... }
        rslt = []
        
        for pk, data_dict in self.values_dict.copy().items():
            values_list = data_dict.get(search_field, None)
            if values_list:
                match = False
                _q = self.clean_string(q, search_field)
                if lookup == '__iexact':
                    if any(self.clean_string(s, search_field) == _q for s in values_list):
                        match = True
                elif lookup == '__istartswith':
                    if any(self.clean_string(s, search_field).startswith(_q) for s in values_list):
                        match = True
                else:
                    if any(_q in self.clean_string(s, search_field) for s in values_list):
                        match = True
                if not match and search_field in self.primary_search_fields and len(q.split())>1:
                    # Scramble the order of q, if all bits of it can be found, accept the values_list as a match
                    partial_match_count = 0
                    for i in q.split():
                        i = self.clean_string(i, search_field)
                        if lookup == '__iexact':
                            if any(any(i == v for v in self.clean_string(value, search_field).split()) for value in values_list):
                                partial_match_count += 1
                        elif lookup == '__istartswith':
                            if any(any(v.startswith(i) for v in self.clean_string(value, search_field).split()) for value in values_list):
                                partial_match_count += 1
                    if partial_match_count == len(q.split()):
                        match = True
                if match:
                    rslt.extend(self.append_suffix([(pk, data_dict.get(self.name_field)[0])], search_field, lookup))
                    self.ids_found.add(pk)
                    self.values_dict.pop(pk)
        return rslt
        
    def search(self, q=None):
        if q:
            self.values_dict = self.get_queryset(q).values_dict(*self.search_fields)
        return super().search(q)
