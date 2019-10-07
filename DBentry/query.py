"""
This module contains helper classes that facilitate querying a queryset for a
search term in various degrees of accuracy.
"""
# TODO: the search strategies do not check/catch if a lookup is allowed
from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy


class BaseSearchQuery(object):
    """
    Helper object to facilitate a search on a number of fields with three
    degrees of accuracy (iexact, istartswith, icontains).
    """

    _results = {}  # FIXME: mutable class attribute (THIS IS NOT USED!)

    def __init__(
            self, queryset, search_fields=None, suffix=None, use_suffix=True,
            **kwargs):
        self.search_fields = search_fields or queryset.model.get_search_fields()
        if isinstance(self.search_fields, str):
            self.search_fields = [self.search_fields]
        self.search_fields = list(self.search_fields)  # 'cast' into a list
        self._root_queryset = queryset
        self.ids_found = set()
        if suffix:
            self.suffix = suffix
        elif getattr(queryset.model, 'search_fields_suffixes', None):
            self.suffix = queryset.model.search_fields_suffixes
        else:
            self.suffix = {}
        self.use_suffix = use_suffix
        self.exact_match = False  # FIXME: pointless declaration; exact_match is set in search()

    def get_model_field(self, field_name):
        """Resolve the given field_name into a model field instance."""
        try:
            return get_fields_from_path(
                self._root_queryset.model, field_name)[-1]
        except FieldDoesNotExist:
            return None

    def clean_string(self, s, field_name):
        """
        Remove whitespaces from string 's' and prepare it for caseless
        comparison. If field_name refers to a DateField, make the string
        date isoformat compliant.
        """
        s = str(s).strip().casefold()
        if isinstance(self.get_model_field(field_name), models.DateField):
            # Comparisons with DateFields require a string of format 'yyyy-mm-dd'.
            if '.' in s:
                return "-".join(
                    date_bit.zfill(2) for
                    date_bit in reversed(s.split('.'))
                )
        return s

    def get_queryset(self, q=None):
        return self._root_queryset.all()

    def get_suffix(self, field, lookup=''):
        """
        Return the suffix to append to a search result for the given the field
        name 'field' and the lookup name 'lookup'.
        """
        if field + lookup in self.suffix:
            return self.suffix.get(field + lookup)
        elif field in self.suffix:
            return self.suffix.get(field)
        else:
            return ""

    def append_suffix(self, instances, field, lookup=''):
        """
        Append suffixes to the search results.

        These suffixes (usually just a verbose version of the field name) act
        as hints on why a particular result was found.
        Returns a list of two-tuples:
            (instance pk, string representation of instance + suffix)
        """
        # FIXME: append_suffix does more than its name suggests:
        # it changes the structure of the results
        # NameFieldSearchQuery.append_suffix override changes nothing about
        # suffixes but changes the structure of the results even further
        suffix = self.get_suffix(field, lookup)

        if self.use_suffix and suffix:
            suffix = " ({})".format(suffix)
        return [(o.pk, force_text(o) + suffix) for o in instances]

    def _do_lookup(self, lookup, search_field, q):
        """
        Perform the search on the given search_field using lookup.

        Append suffixes and record the ids of the instances found to excluded
        them from future searches.

        Returns a list of two-tuples:
            (instance pk, string representation of instance + suffix)
        """
        q = self.clean_string(q, search_field)
        qs = self.get_queryset()
        rslt = []
        search_results = qs.exclude(
            pk__in=self.ids_found).filter(**{search_field + lookup: q})
        new_rslts = self.append_suffix(search_results, search_field, lookup)
        self.ids_found.update([pk for pk, name in new_rslts])
        rslt.extend(new_rslts)
        return rslt

    def exact_search(self, search_field, q):
        """
        Perform the search using the 'iexact' lookup.

        If the search returned results, set the exact_match flag.
        """
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and bool(exact):
            self.exact_match = True
        return exact

    def startsw_search(self, search_field, q):
        """Perform the search using the 'istartswith' lookup."""
        return self._do_lookup('__istartswith', search_field, q)

    def contains_search(self, search_field, q=None):
        """Perform the search using the 'icontains' lookup."""
        return self._do_lookup('__icontains', search_field, q)

    def search(self, q):
        """
        Start point of the search process. Prepare instance variables for a
        new search and begin the search.

        Returns a two-tuple:
            - a list of the results
            - a boolean indicating that an exact match was found
        """
        if not q:
            return self._root_queryset, False

        self.ids_found = set()
        self.exact_match = False
        rslt = self._search(q)
        return rslt, self.exact_match

    def _search(self, q):
        """
        Implement the search strategy.

        For each field in search_fields perform three lookups.
        """
        rslt = []
        for search_field in self.search_fields:
            rslt.extend(
                self.exact_search(search_field, q)
                + self.startsw_search(search_field, q)
                + self.contains_search(search_field, q)
            )
        return rslt


class PrimaryFieldsSearchQuery(BaseSearchQuery):
    """
    A search that visually separates 'strong' results from 'weak' results.

    Using the two lists of queriable field paths 'primary_search_fields' and
    'secondary_search_fields', the results can be categorized into two groups.
    A result is regarded as 'strong' if it was found by searching the values
    of a 'primary search field' or if it was a result of an iexact lookup on a
    'secondary search field'.
    Any results from istartswith/icontains lookups on secondary search fields
    are categorized as 'weak' results.
    Within the result list, these two categories are separated by an artifically
    inserted result (the separator).

    Class attributes:
        - weak_hits_sep (str): template for the separator.
        - separator_width (int): the desired length of the separator string
            after formatting. If the separator is shorter than the specified
            length, it is padded with hyphens.
    """

    weak_hits_sep = gettext_lazy('weak hits for "{q}"')
    separator_width = 36  # Select2 result box is 36 digits wide

    def __init__(
            self, queryset, use_separator=True, primary_search_fields=None,
            *args, **kwargs):
        """
        Instantiate the PrimaryFieldsSearchQuery helper.

        Prepare the two pivotal lists 'primary_search_fields' and
        'secondary_search_fields'. primary_search_fields is either passed in as
        a keyword argument or derived from the model's attribute with the same
        name. If neither provide a non-empty list, the 'search_fields' list as
        established by super() is used (effectively making this helper the same
        as BaseSearchQuery).
        Any fields declared in 'search_fields' that are not in
        'primary_search_fields' are added to 'secondary_search_fields'.

        Arguments:
            - queryset: the queryset to perform the search on.
            - use_separator (bool): whether to insert the separator into the
                result list.
            - primary_search_fields: a list of queriable field paths
        """
        self.use_separator = use_separator
        if primary_search_fields:
            self.primary_search_fields = primary_search_fields
        else:
            self.primary_search_fields = getattr(
                queryset.model, 'primary_search_fields', [])
        super().__init__(queryset, *args, **kwargs)
        if not self.primary_search_fields:
            self.primary_search_fields = self.search_fields
        elif isinstance(self.primary_search_fields, str):
            self.primary_search_fields = [self.primary_search_fields]
        self.secondary_search_fields = [
            field
            for field in self.search_fields
            if field not in self.primary_search_fields
        ]

    def get_separator(self, q, separator_text=None):
        """Return a string to visually separate results from weak results."""
        separator_text = separator_text or force_text(self.weak_hits_sep)
        separator_text = " " + separator_text.format(q=q).strip() + " "
        return '{:-^{width}}'.format(separator_text, width=self.separator_width)

    def exact_search(self, search_field, q):
        """
        Perform the search using the 'iexact' lookup.

        If the search returned results and was done using a primary search
        field, set the exact_match flag.
        """
        exact = self._do_lookup('__iexact', search_field, q)
        if (not self.exact_match
                and search_field in self.primary_search_fields
                and bool(exact)):
            self.exact_match = True
        return exact

    def _search(self, q):
        """
        Implement the search strategy.

        First get the 'strong' results; perform the three lookups for each
        field in primary_search_fields and the iexact lookup for each field in
        secondary_search_fields.
        Then get the 'weak' results from istartswith and icontains lookups on
        fields in secondary_search_fields.
        If use_separator is True and weak results were found, insert a
        separator inbetween the two categories.
        """
        rslt = []
        for search_field in self.primary_search_fields:
            rslt.extend(
                self.exact_search(search_field, q)
                + self.startsw_search(search_field, q)
                + self.contains_search(search_field, q)
            )
        for search_field in self.secondary_search_fields:
            rslt.extend(self.exact_search(search_field, q))

        weak_hits = []
        for search_field in self.secondary_search_fields:
            weak_hits.extend(
                self.startsw_search(search_field, q)
                + self.contains_search(search_field, q)
            )
        if weak_hits:
            if self.use_separator and len(rslt):
                weak_hits.insert(0, (0, self.get_separator(q)))
            rslt.extend(weak_hits)
        return rslt


class NameFieldSearchQuery(PrimaryFieldsSearchQuery):
    """Use the values of the 'name_field' as string representations of the results."""

    # TODO: make NameFieldSearchQuery a mixin for ValuesDictSearchQuery

    name_field = None  # FIXME: useless declaration

    def __init__(self, queryset, *args, **kwargs):
        # FIXME: name_field should be an optional keyword argument
        if kwargs.get('name_field'):
            self.name_field = kwargs.pop('name_field')
        else:
            self.name_field = getattr(queryset.model, 'name_field', None)
        super().__init__(queryset, *args, **kwargs)
        if not self.name_field:
            # If no name_field could be found, take the first field of either
            # primary or secondary_search_fields.
            if self.primary_search_fields:
                self.name_field = self.primary_search_fields[0]
            else:
                self.name_field = self.secondary_search_fields[0]
        self._root_queryset = self._root_queryset.values_list('pk', self.name_field)

    def append_suffix(self, tuple_list, field, lookup=''):
        # FIXME: renaming argument tuple_list could be confusing!
        suffix = self.get_suffix(field, lookup)

        if self.use_suffix and suffix:
            suffix = " ({})".format(suffix)
        return [
            (pk, name + suffix) for pk, name in tuple_list
        ]


class ValuesDictSearchQuery(NameFieldSearchQuery):
    """Fetch all the relevant data first and then do a search in memory."""

    # FIXME: init must check that the queryset is an instance of MIZQuerySet:
    # values_dict must be available.

    def get_queryset(self, q):
        # To limit the length of values_dict, exclude any records that do not
        # at least icontain q in any of the search_fields.
        qobjects = models.Q()
        for search_field in self.search_fields:
            for i in q.split():
                qobjects |= models.Q((
                    search_field + '__icontains',
                    self.clean_string(i, search_field)
                ))
        return self._root_queryset.filter(qobjects)

    def _do_lookup(self, lookup, search_field, q):
        """
        Perform the search for search term 'q' on field 'search_field' using
        lookup 'lookup' within the data (self.values_dict) fetched.
        """
        # values_dict is a dict of dicts of lists!:
        # {pk_1: {field_a: [values,...], field_b: [values...], ...}
        #  pk_2: {}, ...}
        rslt = []

        for pk, data_dict in self.values_dict.copy().items():
            values_list = data_dict.get(search_field, None)
            # TODO: if not values_list: continue (reduce indentations)
            if values_list:
                match = False
                _q = self.clean_string(q, search_field)  # FIXME: why clean it every iteration?
                if lookup == '__iexact':
                    if any(self.clean_string(s, search_field) == _q for s in values_list):
                        match = True
                elif lookup == '__istartswith':
                    if any(self.clean_string(s, search_field).startswith(_q) for s in values_list):
                        match = True
                else:
                    if any(_q in self.clean_string(s, search_field) for s in values_list):
                        match = True
                if not match and search_field in self.primary_search_fields and len(q.split()) > 1:
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
