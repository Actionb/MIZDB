from django.contrib.postgres.search import SearchRank, SearchQuery, SearchVector
from django.db.models import F, Q
from django.contrib.admin.utils import get_fields_from_path

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
        return SearchQuery(search_term, config=config, search_type=search_type)

    def _get_related_search_vectors(self):
        vectors = {}
        for field_path in self.model.related_search_vectors:
            vectors[field_path] = F(field_path)
        return vectors

#    def search(self, search_term, search_type='plain'):
#        simple_query = self._get_search_query(
#            search_term, config=self.simple_config, search_type=search_type)
#        stemmed_query = self._get_search_query(
#            search_term, config=self.stemmed_config, search_type=search_type)
#        field_name = self._get_search_vector_field().name
#        search_rank = SearchRank(F(field_name), simple_query) + SearchRank(F(field_name), stemmed_query)
#        annotations = {'rank': search_rank}
#        filter = Q(**{field_name: simple_query}) | Q(**{field_name: stemmed_query})
#        for field_path, search_vector in self._get_related_search_vectors():
#            filter |= Q(field_path=simple_query)
#            annotations[field_path] = search_vector
#        return self.annotate(**annotations).filter(filter).order_by('-rank').distinct()

    def search(self, search_term, search_type='plain'):
        # TODO: try to find a way to include the combined_vector in the rank
        # TODO: use one simple_query filter (instead of one + one for each related_search_vector)
        simple_query = self._get_search_query(
            search_term, config=self.simple_config, search_type=search_type)
        stemmed_query = self._get_search_query(
            search_term, config=self.stemmed_config, search_type=search_type)
        combined_vector = search_vector = self._get_search_vector_field()
        filter = Q(**{search_vector.name: simple_query}) | Q(**{search_vector.name: stemmed_query})
        for field_path, related_search_vector in self._get_related_search_vectors().items():
            related_search_vector = get_fields_from_path(self.model, field_path)[-1]
            combined_vector = combined_vector + related_search_vector  # NOTE: combining *FIELDS* here, not vectors!
            filter |= Q(**{field_path: simple_query})
        search_rank = SearchRank(search_vector, simple_query) + SearchRank(search_vector, stemmed_query)
        return self.annotate(rank=search_rank).filter(filter).order_by('-rank').distinct()
        
        
        
        
        
