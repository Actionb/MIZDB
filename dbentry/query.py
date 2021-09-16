"""
This module contains helper classes that facilitate querying a queryset for a
search term in various degrees of accuracy (iexact, istartswith, icontains).
"""
from typing import Any, Dict, List, Optional, Sequence, Set, TYPE_CHECKING, Tuple, Union

from django.contrib.admin.utils import get_fields_from_path
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.db.models import Field, Model, QuerySet
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy

if TYPE_CHECKING:
    # Avoid circular imports.
    from dbentry.managers import MIZQuerySet

ResultList = List[Tuple[int, str]]


class BaseSearchQuery(object):
    """
    Helper object to facilitate a search on a number of fields with three
    degrees of accuracy (iexact, istartswith, icontains).

    Attributes:
        - search_fields (list): the list of field names to include in the filter
        - ids_found (set): the set of model instance id's found
        - suffixes (dict): a dictionary of field names to suffixes. If a result
          was found from querying a field defined in the suffixes dict, the
          suffix will be appended to the label of that result.
        - use_suffixes (bool): whether to append suffixes to result labels
        - exact_match (bool): if True, the query with 'iexact' returned a result
    """

    def __init__(
            self,
            queryset: QuerySet,
            search_fields: Union[Sequence, str, None] = None,
            suffixes: Optional[Dict[str, str]] = None,
            use_suffix: bool = True,
            **kwargs: Any
    ) -> None:
        """Initialize the helper object."""
        self._root_queryset: QuerySet = queryset
        self.ids_found: Set[int] = set()
        self.use_suffix: bool = use_suffix
        self.exact_match: bool = False

        search_fields = search_fields or queryset.model.get_search_fields()
        if isinstance(search_fields, str):
            self.search_fields = [search_fields]
        else:
            self.search_fields = list(search_fields)  # 'cast' into a list
        if suffixes:
            self.suffixes = suffixes
        elif getattr(queryset.model, 'search_fields_suffixes', None):
            self.suffixes = queryset.model.search_fields_suffixes
        else:
            self.suffixes = {}

    def get_model_field(self, field_name: str) -> Optional[Field]:
        """Resolve the given field_name into a model field instance."""
        try:
            return get_fields_from_path(self._root_queryset.model, field_name)[-1]
        except FieldDoesNotExist:
            return None

    @staticmethod
    def clean_string(s: str) -> str:
        """
        Remove whitespaces from string ``s`` and prepare it for case
        insensitive comparison.
        """
        return str(s).strip().lower()

    def clean_q(self, q: str, field_name: str) -> str:
        """
        Clean the search term ``q``. If field_name refers to a DateField, make
        ``q`` date isoformat compliant.
        """
        q = self.clean_string(q)
        if isinstance(self.get_model_field(field_name), models.DateField):
            # Comparisons with DateFields require a string of format 'yyyy-mm-dd'.
            if '.' in q:
                return "-".join(
                    date_bit.zfill(2)
                    for date_bit in reversed(q.split('.'))
                )
        return q

    def get_queryset(self, q: str = '') -> QuerySet:
        return self._root_queryset.all()

    def get_suffix(self, field: str, lookup: str = '') -> str:
        """
        Return the suffix to append to a search result for the given the field
        name ``field`` and the lookup name ``lookup``.
        """
        if field + lookup in self.suffixes:
            return self.suffixes[field + lookup]
        elif field in self.suffixes:
            return self.suffixes[field]
        else:
            return ""

    def append_suffix(self, label: str, suffix: str) -> str:
        """
        Append the given suffix to the result's label.

        These suffixes (usually just a verbose version of the field name) act
        as hints on why a particular result was found.
        """
        if self.use_suffix and suffix:
            return "%s (%s)" % (label, suffix)
        return label

    def create_result_list(
            self,
            search_results: Union[QuerySet, ResultList],
            search_field: str,
            lookup: str = ''
    ) -> ResultList:
        """
        Create the result list and record each results' id.

        Returns a list of two-tuples:
            (instance pk, string representation of instance + suffix)
        """
        suffix = self.get_suffix(search_field, lookup)
        results = []
        for item in search_results:
            result = self.create_result_item(item, suffix)
            self.ids_found.add(result[0])
            results.append(result)
        return results

    def create_result_item(self, result: Model, suffix: str) -> Tuple[int, str]:
        """Append the suffix and return an object for the result list."""
        pk, name = self.get_values_for_result(result)
        return pk, self.append_suffix(name, suffix)

    def get_values_for_result(self, result: Model) -> Tuple[int, str]:
        """Return the id and a label from the given model instance result."""
        return result.pk, force_text(result)

    def _do_lookup(self, lookup: str, search_field: str, q: str) -> ResultList:
        """
        Perform a query on the given search_field name using ``lookup`` and
        return the results as modified by create_result_list.
        """
        search_results = (
            self.get_queryset()
            .exclude(pk__in=self.ids_found)
            .filter(**{search_field + lookup: q})
        )
        return self.create_result_list(search_results, search_field, lookup)

    def exact_search(self, search_field: str, q: str) -> ResultList:
        """
        Perform the search using the 'iexact' lookup.

        If the search returned results, set the ``exact_match`` flag.
        """
        exact = self._do_lookup('__iexact', search_field, q)
        if not self.exact_match and bool(exact):
            self.exact_match = True
        return exact

    def startsw_search(self, search_field: str, q: str) -> ResultList:
        """Perform the search using the 'istartswith' lookup."""
        return self._do_lookup('__istartswith', search_field, q)

    def contains_search(self, search_field: str, q: str) -> ResultList:
        """Perform the search using the 'icontains' lookup."""
        return self._do_lookup('__icontains', search_field, q)

    def search(self, q: str, ordered: bool = False) -> Tuple[Union[ResultList, QuerySet], bool]:
        """
        Start point of the search process. Prepare instance variables for a
        new search and begin the search.

        By default, the order of the results depends on the search strategy.
        If ``ordered`` is True, results will be ordered according to the order
        established in the queryset instead.

        Returns a two-tuple:
            - a list of the results (or the root queryset if no search term)
            - a boolean indicating that an exact match was found
        """
        if not q:
            return self._root_queryset, False

        self.ids_found = set()
        self.exact_match = False
        result = self._search(q)
        if result and ordered and self._root_queryset.ordered:
            result = self.reorder_results(result)
        return result, self.exact_match

    def reorder_results(self, results: ResultList) -> ResultList:
        """
        Reorder the results according to the order established by the root
        queryset.
        """
        ids = list(self._root_queryset.values_list('pk', flat=True))
        return sorted(results, key=lambda result_item: ids.index(result_item[0]))

    def _search(self, q: str) -> ResultList:
        """
        Implement the search strategy.

        For each field in search_fields perform three lookups.
        """
        result = []
        for search_field in self.search_fields:
            cleaned_q = self.clean_q(q, search_field)
            result.extend(
                self.exact_search(search_field, cleaned_q)
                + self.startsw_search(search_field, cleaned_q)
                + self.contains_search(search_field, cleaned_q)
            )
        return result


class PrimaryFieldsSearchQuery(BaseSearchQuery):
    """
    A search that visually separates 'strong' results from 'weak' results.

    Using the two lists of queryable (as in: can be used in a query) field paths
    ``primary_search_fields`` and ``secondary_search_fields``, the results can
    be categorized into two groups.
    A result is regarded as 'strong' if it was found by searching the values
    of a primary search field or if it was a result of an *iexact* lookup on a
    secondary search field.
    Any results from istartswith/icontains lookups on secondary search fields
    are categorized as 'weak' results.
    Within the result list, these two categories are separated by an
    artificially inserted result (the separator).

    Attributes:
        - weak_hits_sep (str): format template for the separator
        - separator_item_id (int): the 'id' of the separator item; defaults to 0  # TODO: separator_item_id does not need to be an attribute if it can only ever be 0 or None  # noqa
          as no model instance ever has an id of value 0
        - separator_width (int): the desired length of the separator string
          after formatting. If the separator is shorter than the specified
          length, it is padded with hyphens.
    """

    weak_hits_sep = gettext_lazy('weak hits for "{q}"')
    separator_item_id = 0
    separator_width = 36  # Select2 result box is 36 digits wide

    def __init__(
            self,
            queryset: QuerySet,
            *args: Any,
            use_separator: bool = True,
            primary_search_fields: Optional[Sequence[str]] = None,
            **kwargs: Any
    ) -> None:
        """
        Instantiate the PrimaryFieldsSearchQuery helper.

        Prepare the two pivotal lists ``primary_search_fields`` and
        ``secondary_search_fields``. primary_search_fields is either passed in
        as a keyword argument or derived from the model class attribute with
        the same name. If neither provide a non-empty list, the 'search_fields'
        list as established by super() is used (effectively making this helper
        the same as BaseSearchQuery).
        Any fields declared in 'search_fields' that are not in
        'primary_search_fields' are added to 'secondary_search_fields'.

        Args:
            queryset: the queryset to perform the search on
            use_separator (bool): whether to insert the separator into the
              result list
            primary_search_fields: a list of queryable field paths
        """
        super().__init__(queryset, *args, **kwargs)

        if primary_search_fields:
            self.primary_search_fields = primary_search_fields
        else:
            self.primary_search_fields = getattr(
                queryset.model, 'primary_search_fields', []
            )
        if not self.primary_search_fields:
            self.primary_search_fields = self.search_fields
        elif isinstance(self.primary_search_fields, str):
            self.primary_search_fields = [self.primary_search_fields]

        self.secondary_search_fields = [
            field
            for field in self.search_fields
            if field not in self.primary_search_fields
        ]
        self.use_separator = use_separator

    def create_separator_item(self, q: str, separator_text: str = '') -> Tuple[int, str]:
        """
        Return a result item that acts as a visual separator between strong
        and weak results.
        """
        separator_text = separator_text or force_text(self.weak_hits_sep)
        separator_text = " " + separator_text.format(q=q).strip() + " "
        return (
            self.separator_item_id,
            '{:-^{width}}'.format(separator_text, width=self.separator_width)
        )

    def exact_search(self, search_field: str, q: str) -> ResultList:
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

    def _search(self, q: str) -> ResultList:
        """
        Implement the search strategy.

        First get the 'strong' results; perform the three lookups for each
        field in primary_search_fields and the iexact lookup for each field in
        secondary_search_fields.
        Then get the 'weak' results from istartswith and icontains lookups on
        fields in secondary_search_fields.
        If use_separator is True and weak results were found, insert a
        separator in between the two categories.
        """
        results = []
        for search_field in self.primary_search_fields:
            cleaned_q = self.clean_q(q, search_field)
            results.extend(
                self.exact_search(search_field, cleaned_q)
                + self.startsw_search(search_field, cleaned_q)
                + self.contains_search(search_field, cleaned_q)
            )
        for search_field in self.secondary_search_fields:
            cleaned_q = self.clean_q(q, search_field)
            results.extend(self.exact_search(search_field, cleaned_q))

        weak_hits = []
        for search_field in self.secondary_search_fields:
            cleaned_q = self.clean_q(q, search_field)
            weak_hits.extend(
                self.startsw_search(search_field, cleaned_q)
                + self.contains_search(search_field, cleaned_q)
            )
        if weak_hits:
            if self.use_separator and len(results):
                weak_hits.insert(0, self.create_separator_item(q))
            results.extend(weak_hits)
        return results

    def reorder_results(self, results: ResultList) -> ResultList:
        """
        Reorder the results according to the order established by the root
        queryset.
        Strong and weak results will be ordered within their respective group
        if a separator is used (strong results are only ordered with other
        strong results, etc.).
        """
        # If there is no separator item, do not differentiate between strong
        # and weak results.
        result_ids = [result_item[0] for result_item in results]
        if not self.use_separator or self.separator_item_id not in result_ids:
            return super().reorder_results(results)

        ids = list(self._root_queryset.values_list('pk', flat=True))
        sep_index = result_ids.index(self.separator_item_id)
        # Now split the results into strong and weak results and order
        # both groups individually according to the order in the root queryset.
        strong, weak = results[:sep_index], results[sep_index + 1:]

        def comp_func(result_item):
            return ids.index(result_item[0])

        ordered_results = sorted(strong, key=comp_func)
        # Put the separator item back in.
        ordered_results.append(results[sep_index])
        ordered_results.extend(sorted(weak, key=comp_func))
        return ordered_results


class NameFieldSearchQuery(PrimaryFieldsSearchQuery):
    """
    Use the values of the 'name_field' as string representations of the results.
    """

    def __init__(
            self,
            queryset: QuerySet,
            *args: Any,
            name_field: Optional[str] = None,
            **kwargs: Any
    ) -> None:
        if name_field:
            self.name_field = name_field
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
        # Limit the queryset to only include primary keys and the values of the
        # name fields:
        self._root_queryset = self._root_queryset.values_list(
            'pk', self.name_field
        )

    def get_values_for_result(self, result: Tuple[int, str]) -> Tuple[int, str]:
        """
        Return the id and a label from the given result.

        In the case of NameFieldSearchQuery, the results are two tuples instead
        of model instances.
        """
        return result


class ValuesDictSearchQuery(NameFieldSearchQuery):
    """Fetch all the relevant data first and then do a search in memory."""

    def get_queryset(self, q: str = '') -> 'MIZQuerySet':
        # To limit the length of values_dict, exclude any records that do not
        # at least icontain one 'word' of ``q`` in any of the search_fields.
        qobjects = models.Q()
        for search_field in self.search_fields:
            for i in q.split():
                qobjects |= models.Q(
                    (
                        search_field + '__icontains',
                        self.clean_q(i, search_field)
                    )
                )
        return self._root_queryset.filter(qobjects)

    def _do_lookup(self, lookup: str, search_field: str, q: str) -> ResultList:
        """
        Perform the search for search term ``q`` on field ``search_field``
        using lookup ``lookup`` within the data (self.values_dict) fetched.
        """
        search_results = []

        def filter_func(search_term):
            search_term = self.clean_q(search_term, search_field)

            def inner(s):
                """The filter function for the filter iterator."""
                s = self.clean_string(s)
                if lookup == '__iexact':
                    return search_term == s
                elif lookup == '__istartswith':
                    return s.startswith(search_term)
                return search_term in s

            return inner

        # values_dict is a OrderedDict of dicts of lists!:
        # OrderedDict({
        #   pk_1: {field_a: [values,...], field_b: [values...], ...}
        #   pk_2: {},
        #   ...
        # })
        for pk, data_dict in self.values_dict.copy().items():
            values_list = data_dict.get(search_field, None)
            if not values_list:
                continue
            match = any(filter(filter_func(q), values_list))

            if (not match
                    and lookup != '__icontains'
                    and search_field in self.primary_search_fields
                    and len(q.split()) > 1):
                # 'q' is more than one word; try an order-independent search.
                # If a value in values_list contains a match for each word in
                # 'q', accept the values_list as a match.
                # 'beep boop' would be found by searching for 'boop beep'.
                for value in values_list:
                    for bit in q.split():
                        if not any(filter_func(bit)(word) for word in value.split()):
                            break
                    else:
                        # The inner loop ran without break;
                        # all words of 'q' can be found in 'value'.
                        match = True
                        break

            if match:
                # Create the result list and remove this data_dict from
                # values_dict for future lookups.
                label = self.values_dict.pop(pk)[self.name_field][0]
                search_results.extend(
                    self.create_result_list(
                        search_results=[(pk, label)],
                        search_field=search_field,
                        lookup=lookup
                    )
                )
        return search_results

    def search(self, q: str, *args: Any, **kwargs: Any) -> Tuple[Union[ResultList, QuerySet], bool]:
        if q:
            self.values_dict = self.get_queryset(q).values_dict(*self.search_fields)
        return super().search(q, *args, **kwargs)
