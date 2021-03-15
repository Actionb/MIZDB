from django.contrib.postgres.search import SearchRank, SearchQuery
from django.db.models import F, Q

from dbentry.db.base import SearchVectorField


class TextSearchQuerySetMixin(object):

    search_vector_field_class = SearchVectorField
    simple_config = 'simple'
    stemmed_config = 'german'

    def _get_search_vector_field(self):
        for field in self.model._meta.get_fields():
            if isinstance(field, self.search_vector_field_class):
                return field

    def _get_stemmed_languages(self, search_vector_field):
        """Return extra configs declared on the search vector field that aren't the default."""
        # TODO: 'stemmed' might not be correct word for the configs that aren't 'simple'
        configs = set()
        for column in search_vector_field.columns:
            if column.language != self.simple_config:
                configs.add(column.language)
        return configs

    def _get_search_query(self, search_term, config, search_type):
        """Return a SearchQuery instance. Modify the search term """
        if config == 'simple' and search_type != 'raw':
            # For name lookups, the search term should be interpreted as a
            # prefix. Modify the search term to specify prefix matching (:*).
            # If search_type is 'raw', expect the search term to have already
            # been modified to be used as it is.
            search_type = 'raw'
            search_term = ' & '.join(word for word in search_term.split()) + ':*'
        return SearchQuery(search_term, config=config, search_type=search_type)

    def _get_related_search_vectors(self):
        """
        Return search vector (fields) of models that are related to this model.
        """
        vectors = {}
        for field_path in self.model.related_search_vectors:
            vectors[field_path] = F(field_path)
        return vectors

    def search(self, search_term, search_type='plain'):
        if not search_term:
            return self
        simple_query = self._get_search_query(
            search_term, config=self.simple_config, search_type=search_type)
        stemmed_query = self._get_search_query(
            search_term, config=self.stemmed_config, search_type=search_type)
        # TODO: catch _get_search_vector_field returning None
        field_name = self._get_search_vector_field().name
        search_rank = SearchRank(F(field_name), simple_query) + SearchRank(F(field_name), stemmed_query)
        filter = Q(**{field_name: simple_query}) | Q(**{field_name: stemmed_query})
        for field_path, search_vector in self._get_related_search_vectors().items():
            # Include related search vector fields in the filter:
            filter |= Q(**{field_path: simple_query})  # NOTE: simple query only?
        # TODO: extend ordering by default order
        return self.annotate(rank=search_rank).filter(filter).order_by('-rank').distinct()
