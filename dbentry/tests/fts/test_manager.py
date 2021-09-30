from unittest.mock import patch

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorExact
from django.db import models
from django.db.models.expressions import CombinedExpression
from django.test import TestCase

from dbentry.fts.fields import SearchVectorField
from dbentry.fts.manager import TextSearchQuerySetMixin


class TestTextSearchQuerySetMixin(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        class TestQuerySet(TextSearchQuerySetMixin, models.QuerySet):
            search_vector_field_name = 'svf'

        class Alias(models.Model):
            fts = SearchVectorField()

        class TestModel(models.Model):
            svf = SearchVectorField()
            alias = models.ForeignKey(Alias, on_delete=models.CASCADE)
            objects = TestQuerySet.as_manager()
            related_search_vectors = ['alias__fts']

        cls.model = TestModel
        cls.opts = TestModel._meta
        cls.alias_opts = Alias._meta

    def setUp(self):
        super().setUp()
        self.queryset = self.model.objects.all()

    # noinspection SpellCheckingInspection
    def test_get_search_query(self):
        # Assert that get_search_query prepares the search term (escape & strip
        # each word, and add prefix matching), and that it sets the search_type
        # to 'raw', for any SearchQuery with config='simple' that is not already
        # 'raw' (in which case it is assumed, that the search term has been
        # prepared already).
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='simple', search_type='phrase'
        )
        self.assertEqual(search_query.value, "'''Ardal''' & '''O''' & '''Hanlon''':*")
        self.assertEqual(search_query.search_type, 'raw')

        # config is not 'simple', leave the search term as is:
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='german', search_type='phrase'
        )
        self.assertEqual(search_query.value, "Ardal O'Hanlon ")
        self.assertEqual(search_query.search_type, 'phrase')

        # 'raw' search type, leave the search term as is:
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='simple', search_type='raw'
        )
        self.assertEqual(search_query.value, "Ardal O'Hanlon ")
        self.assertEqual(search_query.search_type, 'raw')

    def test_get_related_search_vectors_no_attr(self):
        # Assert that an empty dictionary is returned, if the queryset model
        # has no related_search_vectors attribute.
        with patch.object(self.queryset, 'model') as mocked_model:
            delattr(mocked_model, 'related_search_vectors')
            self.assertEqual(self.queryset._get_related_search_vectors(), {})

    def test_get_related_search_vectors(self):
        # Assert that get_related_search_vectors returns the search vectors
        # declared by the queryset model.
        self.assertEqual(
            self.queryset._get_related_search_vectors(),
            {'alias__fts': models.F('alias__fts')}
        )

    def test_search_filters(self):
        # Assert that the queryset returned by search() has the expected
        # filters.
        queryset = self.queryset.search('Hovercraft')
        self.assertTrue(queryset.query.has_filters())

        where_node = queryset.query.where.children[0]
        self.assertEqual(where_node.connector, 'OR')
        # 2 exact lookups (one simple, one stemmed) for the field 'svf' and one
        # exact lookup for the related search vector 'alias__fts'
        self.assertEqual(len(where_node.children), 3)
        simple, stemmed, related = where_node.children

        self.assertIsInstance(simple, SearchVectorExact)
        col, query = simple.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        # query.config will be a Value expression
        self.assertEqual(query.config.value, 'simple')
        self.assertEqual(query.search_type, 'raw')

        self.assertIsInstance(stemmed, SearchVectorExact)
        col, query = stemmed.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "Hovercraft")
        self.assertEqual(query.config.value, 'german')
        self.assertEqual(query.search_type, 'plain')

        self.assertIsInstance(related, SearchVectorExact)
        col, query = related.get_source_expressions()
        self.assertEqual(col.target, self.alias_opts.get_field('fts'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        self.assertEqual(query.config.value, 'simple')
        self.assertEqual(query.search_type, 'raw')

    def test_search_rank_annotation(self):
        # Assert that the queryset returned by search() has the expected rank
        # annotation.
        queryset = self.queryset.search('Hovercraft')

        # Check search rank annotation:
        self.assertIn('rank', queryset.query.annotations)
        rank_expression = queryset.query.annotations['rank']
        self.assertIsInstance(rank_expression, CombinedExpression)
        self.assertEqual(rank_expression.connector, '+')
        lhs, rhs = rank_expression.get_source_expressions()

        # lhs should be the search rank with the simple search query
        self.assertIsInstance(lhs, SearchRank)
        col, query = lhs.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        # query.config will be a Value expression
        self.assertEqual(query.config.value, 'simple')
        self.assertEqual(query.search_type, 'raw')

        # rhs should be the search rank with the stemmed search query
        self.assertIsInstance(rhs, SearchRank)
        col, query = rhs.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "Hovercraft")
        self.assertEqual(query.config.value, 'german')
        self.assertEqual(query.search_type, 'plain')

    def test_search_no_search_term(self):
        # Assert that no filters or annotations are added to the queryset if no
        # search term is provided.
        queryset = self.queryset.search('')
        self.assertFalse(queryset.query.has_filters())
        self.assertFalse(queryset.query.annotations)

    def test_search_no_search_vector_field_name(self):
        # Assert that no filters or annotations are added to the queryset if
        # the queryset model is missing the attribute that
        # search_vector_field_name refers to.
        with patch.object(self.queryset, 'model') as mocked_model:
            delattr(mocked_model, self.queryset.search_vector_field_name)
            queryset = self.queryset.search('Hovercraft')
            self.assertFalse(queryset.query.has_filters())
            self.assertFalse(queryset.query.annotations)
