from typing import Any, Union

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Q


class TextSearchQuerySetMixin(object):
    """
    Mixin for QuerySet classes that adds a search() text search method.

    Attributes:
        - search_vector_field_name (str): the name of the SearchVectorField on
          the model of this queryset
        - simple_config (str): postgres text search config name for queries
          without stemming
        - stemmed_config (str): postgres text search config name for queries
          that use natural language stemming
    """

    search_vector_field_name = '_fts'
    simple_config = 'simple'
    stemmed_config = 'german'

    def _get_search_query(self, search_term: str, config: str, search_type: str) -> SearchQuery:
        """
        Return a search query using the given search term, config/language and
        search type.

        If the config is 'simple' and the search type is anything but 'raw',
        modify the search term in the following way:
            * replace single quotes
            * escape each word of search term
            * append a prefix matching label to the last word
            * combine the words with a boolean AND (&)
        The search type is then set to 'raw' so that postgres uses to_tsquery
        instead of plainto_tsquery (which would undo the changes made to the
        query text/search term).
        """
        if config == self.simple_config and search_type != 'raw':
            # TODO: maybe search_types like phrase and websearch should be allowed to pass through?
            # For name lookups, the search term should be interpreted as a
            # prefix. Modify the search term to specify prefix matching (:*).
            # If search_type is 'raw', expect the search term to have already
            # been modified to be used as it is.
            if search_term:
                search_type = 'raw'
                # Replace single quotes with a space:
                search_term = search_term.replace("'", ' ')
                # Escape each word:
                words = ["'''" + word + "'''" for word in search_term.split()]
                # Add prefix to last word:
                words[-1] += ':*'
                search_term = ' & '.join(word for word in words)
        return SearchQuery(search_term, config=config, search_type=search_type)

    def _get_related_search_vectors(self) -> Union[dict, dict[str, F]]:
        """
        Get the search vector fields of related models.

        Returns:
            a dictionary of field_path to F(field_path); i.e. the path to the
              related vector field and a query expression that refers to that
              field
        """
        # noinspection PyUnresolvedReferences
        if not hasattr(self.model, 'related_search_vectors'):  # type: ignore[attr-defined]
            return {}
        vectors = {}
        # noinspection PyUnresolvedReferences
        for field_path in self.model.related_search_vectors:  # type: ignore[attr-defined]
            vectors[field_path] = F(field_path)
        return vectors

    def search(self, search_term: str, search_type: str = 'plain') -> Any:
        """Do a full text search for ``search_term``."""
        if not search_term:
            return self
        # noinspection PyUnresolvedReferences
        if not hasattr(self.model, self.search_vector_field_name):  # type: ignore[attr-defined]
            return self
        simple_query = self._get_search_query(
            search_term, config=self.simple_config, search_type=search_type
        )
        stemmed_query = self._get_search_query(
            search_term, config=self.stemmed_config, search_type=search_type
        )

        filters = (
                Q(**{self.search_vector_field_name: simple_query})
                | Q(**{self.search_vector_field_name: stemmed_query})
        )
        for field_path, search_vector in self._get_related_search_vectors().items():
            # Include related search vector fields in the filter:
            filters |= Q(**{field_path: simple_query})  # NOTE: simple query only?

        search_rank = (
                SearchRank(F(self.search_vector_field_name), simple_query)
                + SearchRank(F(self.search_vector_field_name), stemmed_query)
        )
        # noinspection PyUnresolvedReferences,PyProtectedMember
        return (
            self.annotate(rank=search_rank)  # type: ignore[attr-defined]
                .filter(filters)
                .order_by('-rank', *self.model._meta.ordering)  # type: ignore[attr-defined]
                .distinct()
        )
