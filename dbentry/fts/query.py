from typing import Any, Dict, List, Optional, Type, Union

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Model, Q
from django.db.models import Value
from django.db.models.functions import Coalesce, Greatest

from dbentry.fts.fields import SearchVectorField


def _get_search_vector_field(model: Type[Model]) -> Optional[SearchVectorField]:
    """
    Return the first SearchVectorField instance found for the given model.
    """
    # noinspection PyUnresolvedReferences,PyProtectedMember
    for field in model._meta.get_fields():
        if isinstance(field, SearchVectorField):
            return field
    return None


class TextSearchQuerySetMixin(object):
    """
    Mixin for QuerySet classes that adds a search() text search method.

    Attributes:
        - simple_configs: names of postgres text search configs that do
          not normalize words (stemming). 'Plain' search queries using these
          configs will include prefix matching (see  _get_search_query).
    """

    simple_configs = ('simple_unaccent', 'simple')

    def _get_search_query(self, search_term: str, config: str, search_type: str) -> SearchQuery:
        """
        Return a search query using the given search term, config/language and
        search type.

        Modify ``search_term`` to include prefix matching, if no word
        normalization is intended and if ``search_type`` is 'plain'.
        """
        if search_term and config in self.simple_configs and search_type == 'plain':
            # The given config does not use stemming - it makes sense to add
            # prefix matching.
            # Also: search terms for 'raw' queries are expected to be already
            # formatted, and prefix matching does not work for the other search
            # types such as 'phrase' or 'websearch'.

            # Remove single quotes:
            search_term = search_term.replace("'", ' ')
            # Escape each word and add prefix matching to it:
            words = ["'''" + word + "''':*" for word in search_term.split()]
            # Reconnect the words using AND:
            search_term = ' & '.join(word for word in words)
            # In order to not have postgres parse the search term again and
            # undo these changes, set the search_type to 'raw':
            search_type = 'raw'
        return SearchQuery(search_term, config=config, search_type=search_type)

    def _get_related_search_vectors(self) -> List[str]:
        """
        Return a list of field paths to the search vector fields of related
        models.
        """
        return getattr(self.model, 'related_search_vectors', [])  # type: ignore[attr-defined]

    def search(self, search_term: str, search_type: str = 'plain') -> Any:
        """Do a full text search for ``search_term``."""
        if not search_term:
            return self
        # noinspection PyUnresolvedReferences
        search_field = _get_search_vector_field(self.model)  # type: ignore[attr-defined]
        if not search_field:
            return self

        filters = Q()
        model_search_rank = None
        # TODO: django>3.1: add cover_density=True argument to SearchRank?
        #   -> maybe for normalizing queries
        # TODO: django>3.1: add rank normalization: 0 <= rank <= 1
        for column in search_field.columns or ():
            query = self._get_search_query(
                search_term, config=column.language, search_type=search_type
            )
            filters |= Q(**{search_field.name: query})
            rank = SearchRank(F(search_field.name), query)
            if model_search_rank is None:
                model_search_rank = rank
            else:
                model_search_rank += rank

        related_search_rank = None
        # For related vectors, only use a non-stemming config:
        simple_config = 'simple'
        if self.simple_configs:
            simple_config = self.simple_configs[0]
        for field_path in self._get_related_search_vectors():
            # Include related search vector fields in the filter:
            query = self._get_search_query(
                search_term, config=simple_config, search_type=search_type
            )
            filters |= Q(**{field_path: query})
            # The rank function will return NULL, if the related search
            # vector column has no value - i.e. when the row's record has no
            # related items on the related table (nothing to join).
            # NULL would break the summing up of the ranks (comparison with
            # NULL always returns NULL), so use zero instead.
            rank = Coalesce(SearchRank(F(field_path), query), Value(0))
            if related_search_rank is None:
                related_search_rank = rank
            else:
                related_search_rank += rank

        if not filters:
            # Neither of the loops ran: nothing to filter with.
            return self

        if model_search_rank and related_search_rank:
            # To avoid duplicating rows in the results, just use the rank with
            # the highest value.
            # Explanation:
            # For a given 'model rank', the related rank can be 0 (for the
            # related rows that did not produce a match) and not 0 (for the
            # related rows that did produce a match).
            # If we were to just add both ranks up, we'd get two different
            # ranks for the same record: that same the record would then turn
            # up twice in the results.
            # Example:
            #       query for 'hovercraft':
            # model_field | related__field | model_rank | related_rank
            #  hovercraft |   hovercraft   |          1 |            1 (match on related)
            #  hovercraft |  full of eels  |          1 |            0 (no match)
            #  vikings    |   hovercraft   |          0 |            1 (match on related)
            #  vikings    |   egg & spam   |          0 |            0 (no match)
            search_rank = Greatest(model_search_rank, related_search_rank)
        else:
            search_rank = model_search_rank or related_search_rank

        # noinspection PyProtectedMember
        return (
            self.annotate(rank=search_rank)  # type: ignore[attr-defined]
                .filter(filters)
                .order_by('-rank', *self.model._meta.ordering)  # type: ignore[attr-defined]
                .distinct()
        )
