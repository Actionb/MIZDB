from unittest.mock import Mock, patch

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorExact
from django.db import models
from django.db.models import Max
from django.db.models.expressions import CombinedExpression, Value
from django.db.models.functions import Coalesce
from django.db.models.sql.where import NothingNode
from django.test import TestCase

from dbentry import models as _models
from dbentry.factory import make
from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.fts.query import TextSearchQuerySetMixin
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

    def test_search_kalender(self):
        # Assert that a Kalender object can be found using values defined on
        # its parent (BaseBrochure).
        data = {
            # BaseBrochure fields:
            'titel': 'Titel',
            'zusammenfassung': 'Zusammenfassung',
            'bemerkungen': 'Bemerkungen',
            # Kalender's own field:
            'beschreibung': 'Beschreibung'
        }
        obj = make(_models.Kalender, **data)
        control = make(_models.Kalender, titel='nope')
        for field, value in data.items():
            with self.subTest(field=field, value=value):
                results = _models.Kalender.objects.search(search_term=value)
                self.assertIn(obj, results)
                self.assertNotIn(control, results)


class TestTextSearchQuerySetMixin(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        class TestQuerySet(TextSearchQuerySetMixin, models.QuerySet):
            simple_configs = ('simple_unaccent', 'simple')

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
            related_search_vectors = [('alias__fts', 'simple_unaccent')]

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
        # Assert that get_related_search_vectors returns the search vectors and
        # the config declared by the queryset model.
        self.assertEqual(
            self.queryset._get_related_search_vectors(),
            [('alias__fts', 'simple_unaccent')]
        )

    def test_search_filters(self):
        # Assert that the queryset returned by search() has the expected
        # filters.
        queryset = self.queryset.search('Hovercraft')
        self.assertTrue(queryset.query.has_filters())

        where_node = queryset.query.where.children[0]
        self.assertEqual(where_node.connector, 'OR')
        # 2 exact lookups, one for every config declared in the columns for the
        # field 'svf' and one exact lookup for the related search vector
        # 'alias__fts'.
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

    def test_search_rank_annotation(self):
        # Assert that the queryset returned by search() has the expected rank
        # annotation.
        queryset = self.queryset.search('Hovercraft')

        # Check search rank annotation:
        self.assertIn('rank', queryset.query.annotations)
        rank = queryset.query.annotations['rank']
        # rank should be a combined expression, where the lhs (the first
        # expression) is a combined expression of the 'model' ranks.
        self.assertIsInstance(rank, CombinedExpression)
        self.assertEqual(rank.connector, '+')
        model_rank, related_rank = rank.get_source_expressions()

        self.assertIsInstance(model_rank, CombinedExpression)
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

        # related_rank should be a Max aggregate of the 'coalesced' related
        # ranks:
        self.assertIsInstance(related_rank, Max)
        coalesce_func = related_rank.get_source_expressions()[0]
        self.assertIsInstance(coalesce_func, Coalesce)
        related, fallback_value = coalesce_func.get_source_expressions()
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
            rank = queryset.query.annotations['rank']
            # The rank for related vectors should be aggregated using Max and
            # be wrapped in Coalesce:
            self.assertIsInstance(rank, Max)
            coalesce, *filters = rank.get_source_expressions()
            self.assertIsInstance(coalesce, Coalesce)
            search_rank, coalesce_value = coalesce.get_source_expressions()
            self.assertIsInstance(search_rank, SearchRank)
            col, query = search_rank.get_source_expressions()
            self.assertEqual(col.target, self.alias_opts.get_field('fts'))

    def test_search_rank_annotation_model_rank_only(self):
        # Assert that only the rank for the model field appears in the
        # query annotations if no related rank could be built.
        mocked_get_related = Mock(return_value={})
        with patch.object(self.queryset, '_get_related_search_vectors', mocked_get_related):
            queryset = self.queryset.search('Hovercraft')
            self.assertIn('rank', queryset.query.annotations)
            rank = queryset.query.annotations['rank']
            # the rank expression should be the combined expression for the two
            # columns of the model's search vector field
            self.assertIsInstance(rank, CombinedExpression)
            for expr in rank.get_source_expressions():
                col, query = expr.get_source_expressions()
                self.assertEqual(col.target, self.opts.get_field('svf'))

    def test_search_no_columns_no_related_vectors(self):
        # Assert that no filters or annotations are added to the queryset if no
        # columns and no related search vectors were declared.
        mocked_search_field = Mock(columns=None)
        mocked_get_search_field = Mock(return_value=mocked_search_field)
        mocked_get_related = Mock(return_value={})
        with patch('dbentry.fts.query._get_search_vector_field', mocked_get_search_field):
            with patch.object(self.queryset, '_get_related_search_vectors', mocked_get_related):
                queryset = self.queryset.search('Hovercraft')
                self.assertEqual(len(queryset.query.where.children), 1)
                self.assertIsInstance(queryset.query.where.children[0], NothingNode)
                self.assertFalse(queryset.query.annotations)

    def test_search_no_search_term(self):
        # Assert that an empty (using none()) queryset is returned if no search
        # term was provided.
        queryset = self.queryset.search('')
        self.assertEqual(len(queryset.query.where.children), 1)
        self.assertIsInstance(queryset.query.where.children[0], NothingNode)
        self.assertFalse(queryset.query.annotations)
