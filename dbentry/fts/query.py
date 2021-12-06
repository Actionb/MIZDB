from typing import Any, List, Optional, Tuple, Type

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import BooleanField, ExpressionWrapper, F, FloatField, Max, Model, Q, Value
from django.db.models.functions import Coalesce

from dbentry.fts.fields import SearchVectorField

# TODO: SearchVectorFields should be deferred in queries that don't use them
SIMPLE = 'simple_unaccent'
STEMMING = 'german_unaccent'


def _get_search_vector_field(model: Type[Model]) -> Optional[SearchVectorField]:
    """
    Return the first SearchVectorField instance found for the given model.
    """
    # exclude inherited search vector fields:
    # noinspection PyUnresolvedReferences,PyProtectedMember
    for field in model._meta.get_fields(include_parents=False):
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

    simple_configs = (SIMPLE, 'simple')

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

    def _get_related_search_vectors(self) -> List[Tuple[str, str]]:
        """
        Return a list of tuples of (field path, config_name).

        The field path points to the search vector field of a related model to
        be included in a query, and the config_name refers to the search config
        to use in the query on that related field.
        """
        return getattr(self.model, 'related_search_vectors', [])  # type: ignore[attr-defined]

    def search(self, q: str, search_type: str = 'plain', ranked: bool = True) -> Any:
        """
        Do a full text search for search term ``q``.

        If ``ranked`` is True (which is the default) or if the queryset is
        unordered, order the results by how closely they matched the search
        term: exact matches first, then matches that start with the search term,
        then ordered by text search rank, and finally ordered either according
        to the queryset ordering or - if the queryset wasn't ordered - by the
        model's default ordering.
        """
        if not q:
            # noinspection PyUnresolvedReferences
            return self.none()  # type: ignore[attr-defined]

        filters = Q()
        model_search_rank = related_search_rank = None

        # noinspection PyUnresolvedReferences
        model = self.model  # type: ignore[attr-defined]
        search_field = _get_search_vector_field(model)
        if search_field:
            # TODO: django>3.1: add cover_density=True argument to SearchRank?
            #   -> maybe for normalizing queries
            # TODO: django>3.1: add rank normalization: 0 <= rank <= 1
            # Add a query and a rank for every text search config defined on
            # the search vector field's columns:
            configs_seen = set()
            for column in search_field.columns or ():
                if column.language in configs_seen:
                    continue
                configs_seen.add(column.language)
                query = self._get_search_query(
                    q, config=column.language, search_type=search_type
                )
                filters |= Q(**{search_field.name: query})
                rank = SearchRank(F(search_field.name), query)
                if model_search_rank is None:
                    model_search_rank = rank
                else:
                    model_search_rank += rank

        for field_path, config in self._get_related_search_vectors():
            # Include related search vector fields in the filter:
            query = self._get_search_query(
                q, config=config, search_type=search_type
            )
            filters |= Q(**{field_path: query})
            # The rank function will return NULL, if the related search
            # vector column has no value - i.e. when the row's record has no
            # related items on the related table (nothing to join).
            # NULL would break the summing up of the ranks (comparison with
            # NULL always returns NULL), so use zero instead.
            rank = Coalesce(SearchRank(F(field_path), query), Value(0), output_field=FloatField())
            if related_search_rank is None:
                related_search_rank = rank
            else:
                related_search_rank += rank

        if not filters:
            # Neither of the loops ran: nothing to filter with.
            # noinspection PyUnresolvedReferences
            return self.none()  # type: ignore[attr-defined]

        # Only use the rank of the closest matching related row (highest rank).
        # This prevents introducing duplicate rows due to related ranks having
        # different values for the same 'model object'.
        if model_search_rank and related_search_rank:
            search_rank = model_search_rank + Max(related_search_rank)
        else:
            search_rank = model_search_rank or Max(related_search_rank)

        results = self.annotate(rank=search_rank).filter(filters)  # type: ignore[attr-defined]  # noqa
        # noinspection PyUnresolvedReferences
        if ranked or not self.query.order_by:  # type: ignore[attr-defined]
            # Apply ordering to the results.
            # noinspection PyProtectedMember, PyUnresolvedReferences
            ordering = ['-rank', *(self.query.order_by or model._meta.ordering)]  # type: ignore[attr-defined]  # noqa
            if ranked and getattr(model, 'name_field', None):
                name_field = model.name_field
                exact = ExpressionWrapper(
                    Q(**{name_field + '__iexact': q}),
                    output_field=BooleanField()
                )
                startswith = ExpressionWrapper(
                    Q(**{name_field + '__istartswith': q}),
                    output_field=BooleanField()
                )
                ordering = [exact.desc(), startswith.desc()] + ordering
            results = results.order_by(*ordering)
        return results.distinct()
