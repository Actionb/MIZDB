from unittest.mock import patch

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorExact
from django.db import models
from django.db.models.expressions import CombinedExpression
from django.test import TestCase

from dbentry import models as _models
from dbentry.factory import make
from dbentry.fts.fields import SearchVectorField
from dbentry.fts.manager import TextSearchQuerySetMixin
from dbentry.tests.base import DataTestCase


class TestFullTextSearch(DataTestCase):

    model = _models.Band
    raw_data = [
        {
            'band_name': 'Die Ärzte',
            'beschreibung': 'Die deutschen Ärzte mögen Crêpe.',
            'bandalias__alias': 'El Doktores'
        },
        {   # 'control' object:
            'band_name': 'The Beatles',
            'beschreibung': 'The Beatles sollten in keinen Suchergebnissen auftauchen.'
        },
        {'band_name': 'Übermensch'}
    ]

    def test_search_simple(self):
        # Assert that lookups for names return expected results.
        results = self.queryset.search('Die Ärzte')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)

    def test_search_simple_partial(self):
        # Assert that partial lookups for names return expected results.
        for partial_search_term in ['Di', 'Ärz', 'Die Ärz']:
            with self.subTest(search_term=partial_search_term):
                results = self.queryset.search(partial_search_term)
                self.assertEqual(results.count(), 1)
                self.assertEqual(results.get(), self.obj1)

    def test_search_stemming(self):
        # Assert that lookups using natural language return expected results.
        results = self.queryset.search('deutscher Arzt')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)

    def test_unaccent(self):
        # Assert that accents do not influence the search results.
        for search_term in ['Crêpe', 'Crépe', 'Crepe']:
            with self.subTest(search_term=search_term):
                results = self.queryset.search(search_term)
                self.assertEqual(results.count(), 1)
                self.assertEqual(results.get(), self.obj1)

    def test_ranking(self):
        # Assert that the results are ranked as expected.
        #
        # A simple (i.e. not stemmed) query on the field with the heighest
        # weight (field 'band_name') would match obj1. obj1 should therefore
        # have the highest ranking.
        # A stemmed query on 'band_name' would match this next object. Since
        # the search term contains a stop word, the match isn't as exact as the
        # simple query match for obj1.
        other = make(self.model, band_name='Der Arzt')
        # This object contains part of the stemmed query in a field with lower
        # weight - it should come last:
        another = make(
            self.model, band_name='Toten Hosen',
            beschreibung='Sie gehen gerne zum Arzt.'
        )
        self.assertEqual(
            list(self.queryset.search('Die Ärzte').order_by('-rank')),
            [self.obj1, other, another]
        )

    def test_alias_search(self):
        # Assert that objects can be found by searching for an alias.
        results = self.queryset.search('Doktores')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)

    def test_ordering(self):
        # Assert that the result querysets includes the model's default ordering.
        results = self.queryset.search('Die Ärzte')
        for ordering in self.model._meta.ordering:
            self.assertIn(
                ordering, results.query.order_by,
                msg=(
                    "Result queryset ordering does not include the model's "
                    "default ordering.\nResult ordering:%s\nDefault ordering:%s" % (
                        results.query.order_by, self.model._meta.ordering
                    )
                )
            )

    def test_handles_special_characters(self):
        # Assert that queries with tsquery-specific chars are fine.
        chars = ['"', "'", "&", "|",  "<", ">", ":"]
        for special_char in chars:
            with self.subTest(special_char=special_char):
                with self.assertNotRaises(Exception):
                    self.queryset.search('Beep' + special_char)

    def test_search_umlaute(self):
        # Regression test:
        # SQLite performs case sensitive searches for strings containing chars
        # outside the ASCII range (such as Umlaute ä, ö, ü).
        for q in ('ü', 'Ü'):
            with self.subTest(q=q):
                results = self.queryset.search(q)
                self.assertTrue(
                    results,
                    msg="Expected to find matches regardless of case of Umlaut."
                )


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
