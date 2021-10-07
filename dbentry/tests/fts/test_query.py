from unittest.mock import Mock, patch

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorExact
from django.db import models
from django.db.models.expressions import CombinedExpression, Value
from django.db.models.functions import Coalesce, Greatest
from django.test import TestCase

from dbentry import models as _models
from dbentry.factory import make
from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.fts.query import TextSearchQuerySetMixin, _get_search_vector_field
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
        self.assertTrue(results.get().rank)

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

    def test_search_ausgabe(self):
        # Assert that an Ausgabe instance can be found using its _name.
        # This tests the use of the 'simple_numeric' search config that
        # addresses postgres default search configs tripping over string
        # numerics with hyphens.
        obj = make(_models.Ausgabe, ausgabejahr__jahr=2018, ausgabenum__num=3)
        self.assertIn(obj, _models.Ausgabe.objects.search('2018-3'))
        self.assertIn(obj, _models.Ausgabe.objects.search('2018 3'))


class TestTextSearchQuerySetMixin(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        class TestQuerySet(TextSearchQuerySetMixin, models.QuerySet):
            search_vector_field_name = 'svf'

        class Alias(models.Model):
            fts = SearchVectorField()

        class TestModel(models.Model):
            title = models.CharField()
            svf = SearchVectorField(
                columns=[
                    WeightedColumn('title', 'A', 'simple_unaccent'),
                    WeightedColumn('title', 'B', 'german_unaccent')
                ]
            )
            alias = models.ForeignKey(Alias, on_delete=models.CASCADE)
            objects = TestQuerySet.as_manager()
            related_search_vectors = ['alias__fts']

        cls.model = TestModel
        cls.opts = TestModel._meta
        cls.alias_opts = Alias._meta

    def setUp(self):
        super().setUp()
        self.queryset = self.model.objects.all()
        self.queryset.simple_configs = ('simple_unaccent',)

    # noinspection SpellCheckingInspection
    def test_get_search_query(self):
        # Assert that get_search_query prepares the search term (escape & strip
        # each word, and add prefix matching), and that it sets the search_type
        # to 'raw', for any SearchQuery with config='simple_unaccent'.
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='simple_unaccent', search_type='plain'
        )
        self.assertEqual(search_query.value, "'''Ardal''':* & '''O''':* & '''Hanlon''':*")
        self.assertEqual(search_query.search_type, 'raw')

    # noinspection SpellCheckingInspection
    def test_get_search_query_config_not_simple(self):
        # Assert that get_search_query does not modify the search_term or
        # changes the querie's search_type when the config is not registered
        # as a 'simple' (non-normalizing) config.
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='german_unaccent', search_type='plain'
        )
        self.assertEqual(search_query.value, "Ardal O'Hanlon ")
        self.assertEqual(search_query.search_type, 'plain')

    # noinspection SpellCheckingInspection
    def test_get_search_query_search_type_not_plain(self):
        # Assert that get_search_query does not modify the search_term or
        # changes the querie's search_type when the search type is not 'plain'.
        for search_type in ('raw', 'phrase'):  # TODO: django > 3.1: add search_type 'websearch'
            with self.subTest(search_type=search_type):
                search_query = self.queryset._get_search_query(
                    "Ardal O'Hanlon ", config='simple_unaccent', search_type=search_type
                )
                self.assertEqual(search_query.value, "Ardal O'Hanlon ")
                self.assertEqual(search_query.search_type, search_type)

    def test_get_related_search_vectors_no_attr(self):
        # Assert that an empty list is returned, if the queryset model has no
        # related_search_vectors attribute.
        with patch.object(self.queryset, 'model') as mocked_model:
            delattr(mocked_model, 'related_search_vectors')
            self.assertEqual(self.queryset._get_related_search_vectors(), [])

    def test_get_related_search_vectors(self):
        # Assert that get_related_search_vectors returns the search vectors
        # declared by the queryset model.
        self.assertEqual(self.queryset._get_related_search_vectors(), ['alias__fts'])

    def test_search_filters(self):
        # Assert that the queryset returned by search() has the expected
        # filters.
        queryset = self.queryset.search('Hovercraft')
        self.assertTrue(queryset.query.has_filters())

        where_node = queryset.query.where.children[0]
        self.assertEqual(where_node.connector, 'OR')
        # 2 exact lookups (one per column: one simple, one stemmed) for the
        # field 'svf' and one exact lookup for the related search
        # vector 'alias__fts'.
        self.assertEqual(len(where_node.children), 3)
        simple, stemmed, related = where_node.children

        self.assertIsInstance(simple, SearchVectorExact)
        col, query = simple.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        self.assertEqual(query.config, Value('simple_unaccent'))
        self.assertEqual(query.search_type, 'raw')

        self.assertIsInstance(stemmed, SearchVectorExact)
        col, query = stemmed.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "Hovercraft")
        self.assertEqual(query.config, Value('german_unaccent'))
        self.assertEqual(query.search_type, 'plain')

        self.assertIsInstance(related, SearchVectorExact)
        col, query = related.get_source_expressions()
        self.assertEqual(col.target, self.alias_opts.get_field('fts'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        self.assertEqual(query.config, Value('simple_unaccent'))
        self.assertEqual(query.search_type, 'raw')

    def test_search_filters_no_simple_configs(self):
        # Assert that the filters for related search vectors default to
        # 'simple' queries if the queryset specifies no simple_configs.
        with patch.object(self.queryset, 'simple_configs', []):
            queryset = self.queryset.search('Hovercraft')
            related = queryset.query.where.children[0].children[-1]
            self.assertIsInstance(related, SearchVectorExact)
            col, query = related.get_source_expressions()
            self.assertEqual(col.target, self.alias_opts.get_field('fts'))
            self.assertIsInstance(query, SearchQuery)
            self.assertEqual(query.config, Value('simple'))

    def test_search_rank_annotation(self):
        # Assert that the queryset returned by search() has the expected rank
        # annotation.
        queryset = self.queryset.search('Hovercraft')

        # Check search rank annotation:
        self.assertIn('rank', queryset.query.annotations)
        func = queryset.query.annotations['rank']
        # Greatest func is expected, since we have queries for the model's
        # search field and a related search field:
        self.assertIsInstance(func, Greatest)
        model_rank, related_rank = func.get_source_expressions()

        # Inspect the rank for the model field:
        self.assertIsInstance(model_rank, CombinedExpression)
        self.assertEqual(model_rank.connector, '+')
        simple, stemmed = model_rank.get_source_expressions()

        # 'simple' should be the search rank with the simple search query
        self.assertIsInstance(simple, SearchRank)
        col, query = simple.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        # query.config will be a Value expression
        self.assertEqual(query.config, Value('simple_unaccent'))
        self.assertEqual(query.search_type, 'raw')

        # 'stemmed' should be the search rank with the stemmed search query
        self.assertIsInstance(stemmed, SearchRank)
        col, query = stemmed.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "Hovercraft")
        self.assertEqual(query.config, Value('german_unaccent'))
        self.assertEqual(query.search_type, 'plain')

        # The related rank consists of only one item, and thus hasn't been
        # combined.
        # Coalesce is used on every related rank:
        self.assertIsInstance(related_rank, Coalesce)
        related, fallback_value = related_rank.get_source_expressions()
        self.assertIsInstance(fallback_value, Value)
        self.assertEqual(fallback_value.value, 0)
        # 'related' should be the search rank with the simple search query for
        # the related vector field
        self.assertIsInstance(related, SearchRank)
        col, query = related.get_source_expressions()
        self.assertEqual(col.target, self.alias_opts.get_field('fts'))
        self.assertIsInstance(query, SearchQuery)
        self.assertEqual(query.value, "'''Hovercraft''':*")
        self.assertEqual(query.config, Value('simple_unaccent'))
        self.assertEqual(query.search_type, 'raw')

    def test_search_rank_annotation_related_rank_only(self):
        # Assert that only the rank for the related vectors appears in the
        # query annotations if no model rank could be built (f.ex. when the
        # search vector feld was missing columns).
        mocked_search_field = Mock(columns=None)
        mocked_get_search_field = Mock(return_value=mocked_search_field)
        with patch('dbentry.fts.query._get_search_vector_field', mocked_get_search_field):
            queryset = self.queryset.search('Hovercraft')
            self.assertIn('rank', queryset.query.annotations)
            # ranks for related vectors should always be 'coalesced'
            self.assertIsInstance(queryset.query.annotations['rank'], Coalesce)

    def test_search_rank_annotation_model_rank_only(self):
        # Assert that only the rank for the model field appears in the
        # query annotations if no related rank could be built.
        mocked_get_related = Mock(return_value={})
        with patch.object(self.queryset, '_get_related_search_vectors', mocked_get_related):
            queryset = self.queryset.search('Hovercraft')
            self.assertIn('rank', queryset.query.annotations)
            # the rank expression should be the combined expression for the two
            # columns of the model's search vector field
            self.assertIsInstance(queryset.query.annotations['rank'], CombinedExpression)

    def test_search_no_columns_no_related_vectors(self):
        # Assert that no filters or annotations are added to the queryset if no
        # columns and no related search vectors were declared.
        mocked_search_field = Mock(columns=None)
        mocked_get_search_field = Mock(return_value=mocked_search_field)
        mocked_get_related = Mock(return_value={})
        with patch('dbentry.fts.query._get_search_vector_field', mocked_get_search_field):
            with patch.object(self.queryset, '_get_related_search_vectors', mocked_get_related):
                queryset = self.queryset.search('Hovercraft')
                self.assertFalse(queryset.query.has_filters())
                self.assertFalse(queryset.query.annotations)

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
