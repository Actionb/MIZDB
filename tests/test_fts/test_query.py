from unittest.mock import Mock, patch

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVectorExact
from django.db import models
from django.db.models import Max
from django.db.models.expressions import CombinedExpression, Value
from django.db.models.functions import Coalesce
from django.db.models.sql.where import NothingNode
from django.test import TestCase

from dbentry import models as _models
from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.fts.query import TextSearchQuerySetMixin, _get_search_vector_field
from tests.case import DataTestCase
from tests.model_factory import make


class TestGetSearchVectorField(TestCase):
    class ModelA(models.Model):
        title = models.CharField(max_length=100)
        search_field_1 = SearchVectorField(columns=[WeightedColumn('title', 'A', 'simple')])
        search_field_2 = SearchVectorField(columns=[WeightedColumn('title', 'A', 'simple')])

    class ModelB(models.Model):
        title = models.CharField(max_length=100)

    def test(self):
        expected = self.ModelA._meta.get_field('search_field_1')
        self.assertEqual(_get_search_vector_field(self.ModelA), expected)
        self.assertIsNone(_get_search_vector_field(self.ModelB))


class TestFullTextSearch(DataTestCase):
    model = _models.Band

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, band_name='Die Ärzte', bandalias__alias='El Doktores',
            beschreibung='Die deutschen Ärzte mögen Crêpe.'
        )
        # 'Control' object:
        cls.obj2 = make(
            cls.model, band_name='The Beatles',
            beschreibung='The Beatles sollten in keinen Suchergebnissen auftauchen.'
        )

    def test_search_simple(self):
        """Assert that lookups for names return expected results."""
        results = self.queryset.search('Die Ärzte')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)

    def test_search_simple_partial(self):
        """Assert that partial lookups for names return expected results."""
        for partial_search_term in ['Di', 'Ärz', 'Die Ärz']:
            with self.subTest(search_term=partial_search_term):
                results = self.queryset.search(partial_search_term)
                self.assertEqual(results.count(), 1)
                self.assertEqual(results.get(), self.obj1)

    def test_search_stemming(self):
        """Assert that lookups using natural language return expected results."""
        results = self.queryset.search('deutscher Arzt')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)

    def test_unaccent(self):
        """Assert that accents do not influence the search results."""
        for search_term in ['Crêpe', 'Crépe', 'Crepe']:
            with self.subTest(search_term=search_term):
                results = self.queryset.search(search_term)
                self.assertEqual(results.count(), 1)
                self.assertEqual(results.get(), self.obj1)

    def test_ordering_ranked(self):
        """Assert that the results are ordered as expected with ranked=True."""
        # exact matches -> startswith matches -> other
        exact = make(self.model, band_name='Ärzte')
        startsw = make(self.model, band_name='Ärztekammer')
        another = make(
            self.model, band_name='Toten Hosen',
            beschreibung='Sie gehen gerne zum Arzt.'
        )
        self.assertQuerySetEqual(
            [exact, startsw, self.obj1, another],
            self.model.objects.search('Ärzte', ranked=True)
        )

    def test_ordering_respects_specified_ordering(self):
        """Assert that search includes previously specified ordering."""
        self.assertIn(
            '-beschreibung',
            self.queryset.order_by('-beschreibung').search('Ärzte', ranked=True).query.order_by,
        )

    def test_ordering_pk_match(self):
        """Assert that the primary key matches come first before other matches."""
        pk_match = make(self.model)
        exact = make(self.model, band_name=str(pk_match.pk))
        self.assertQuerySetEqual([pk_match, exact], self.model.objects.search(str(pk_match.pk)))

    def test_ordering_not_ranked(self):
        """Assert that the results are ordered as expected with ranked=False."""
        # A simple (i.e. not stemmed) query on the field with the highest
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
        self.assertQuerySetEqual(
            [self.obj1, other, another],
            self.queryset.search('Die Ärzte', ranked=False).order_by('-rank')
        )

    def test_ordering_unordered(self):
        """
        Assert that the initially unordered result queryset includes the
        model's default ordering.
        """
        results = self.queryset.order_by().search('Die Ärzte', ranked=False)
        model_ordering = self.model._meta.ordering
        for ordering in model_ordering:
            self.assertIn(
                ordering, results.query.order_by,
                msg=(
                    "Result queryset ordering does not include the model's default ordering."
                    f"\nResult ordering:{results.query.order_by}\nDefault ordering:{model_ordering}"
                )
            )

    def test_alias_search(self):
        """Assert that objects can be found by searching for an alias."""
        results = self.queryset.search('Doktores')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.get(), self.obj1)
        self.assertTrue(results.get().rank)

    def test_handles_special_characters(self):
        """Assert that queries with tsquery-specific chars work."""
        chars = ['"', "'", "&", "|", "<", ">", ":"]
        for special_char in chars:
            with self.subTest(special_char=special_char):
                with self.assertNotRaises(Exception):
                    self.queryset.search('Beep' + special_char)

    def test_search_ausgabe(self):
        """Assert that an Ausgabe instance can be found using its _name."""
        # This tests the use of the 'simple_numeric' search config that
        # addresses postgres default search configs tripping over string
        # numerics with hyphens.
        obj = make(_models.Ausgabe, ausgabejahr__jahr=2018, ausgabenum__num=3)
        self.assertIn(obj, _models.Ausgabe.objects.search('2018-03'))
        self.assertIn(obj, _models.Ausgabe.objects.search('2018 03'))

    def test_search_kalender(self):
        """
        Assert that a Kalender object can be found using values defined on
        its parent (BaseBrochure).
        """
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
                results = _models.Kalender.objects.search(q=value)
                self.assertIn(obj, results)
                self.assertNotIn(control, results)

    def test_search_person(self):
        """
        Assert that a Person instance can be found using different ways of
        writing a human name.
        """
        obj = make(_models.Person, vorname='Peter', nachname='Lustig')
        for name in ('Peter Lustig', 'Lustig, Peter'):
            with self.subTest(name=name):
                self.assertIn(obj, _models.Person.objects.search(name))

    def test_search_autor(self):
        """
        Assert that an Autor instance can be found using different ways of
        writing an author's name(s).
        """
        obj = make(
            _models.Autor,
            person__vorname='Peter', person__nachname='Lustig', kuerzel='PL'
        )
        names = (
            'Peter Lustig', 'Lustig, Peter', 'Peter (PL) Lustig',
            'Peter Lustig (PL)', 'Lustig, Peter (PL)'
        )
        for name in names:
            with self.subTest(name=name):
                self.assertIn(obj, _models.Autor.objects.search(name))

    def test_search_id(self):
        """Assert that instances can be found using their id."""
        q = str(self.obj1.pk)
        self.assertQuerySetEqual(self.queryset.search(q), [self.obj1])

        # A comma-separated list of ids should be allowed:
        q = f"{self.obj1.pk},{self.obj2.pk}"
        self.assertQuerySetEqual(self.queryset.search(q), [self.obj1, self.obj2])

        # Whitespaces should not influence the search and should be stripped:
        q = f"{self.obj1.pk}  ,     {self.obj2.pk} "
        self.assertQuerySetEqual(self.queryset.search(q), [self.obj1, self.obj2])

    def test_search_id_not_all_numerical_values(self):
        """
        Assert that an id search is only attempted if all values in the search
        term are numeric.
        """
        self.assertFalse(self.queryset.search(f"{self.obj1.pk},Ärzte"))


class TestTextSearchQuerySetMixin(TestCase):

    @classmethod
    def setUpClass(cls):

        class TestQuerySet(TextSearchQuerySetMixin, models.QuerySet):
            simple_configs = ('simple_unaccent', 'simple')

        class MixinTestAlias(models.Model):
            fts = SearchVectorField()

        class MixinTestModel(models.Model):
            title = models.CharField()
            svf = SearchVectorField(
                columns=[
                    WeightedColumn('title', 'A', 'simple_unaccent'),
                    WeightedColumn('title', 'B', 'german_unaccent')
                ]
            )
            alias = models.ForeignKey(MixinTestAlias, on_delete=models.CASCADE)
            objects = TestQuerySet.as_manager()
            related_search_vectors = [('alias__fts', 'simple_unaccent')]

        cls.model = MixinTestModel
        cls.opts, cls.alias_opts = MixinTestModel._meta, MixinTestAlias._meta

        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.queryset = self.model.objects.all()

    def test_get_search_query(self):
        """
        Assert that get_search_query prepares the search term (escape & strip
        each word, and add prefix matching), and that it sets the search_type
        to 'raw', for any SearchQuery with config='simple_unaccent'.
        """
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='simple_unaccent', search_type='plain'
        )
        _config, value = search_query.get_source_expressions()
        self.assertEqual(value.value, "'''Ardal''':* & '''O''':* & '''Hanlon''':*")
        self.assertEqual(search_query.function, 'to_tsquery')

    def test_get_search_query_config_not_simple(self):
        """
        Assert that get_search_query does not modify the search_term or
        changes the query's search_type when the config is not registered
        as a 'simple' (non-normalizing) config.
        """
        search_query = self.queryset._get_search_query(
            "Ardal O'Hanlon ", config='german_unaccent', search_type='plain'
        )
        _config, value = search_query.get_source_expressions()
        self.assertEqual(value.value, "Ardal O'Hanlon ")
        self.assertEqual(search_query.function, 'plainto_tsquery')

    def test_get_search_query_search_type_not_plain(self):
        """
        Assert that get_search_query does not modify the search_term or
        changes the query's search_type when the search type is not 'plain'.
        """
        for search_type in ('raw', 'phrase', 'websearch'):
            with self.subTest(search_type=search_type):
                search_query = self.queryset._get_search_query(
                    "Ardal O'Hanlon ", config='simple_unaccent', search_type=search_type
                )
                _config, value = search_query.get_source_expressions()
                self.assertEqual(value.value, "Ardal O'Hanlon ")
                self.assertIn(
                    search_query.function,
                    ('to_tsquery', 'phraseto_tsquery', 'websearch_to_tsquery')
                )

    def test_get_related_search_vectors_no_attr(self):
        """
        Assert that an empty list is returned, if the queryset model has no
        related_search_vectors attribute.
        """
        with patch.object(self.queryset, 'model') as mocked_model:
            delattr(mocked_model, 'related_search_vectors')
            self.assertEqual(self.queryset._get_related_search_vectors(), [])

    def test_get_related_search_vectors(self):
        """
        Assert that get_related_search_vectors returns the search vectors and
        the config declared by the queryset model.
        """
        self.assertEqual(
            self.queryset._get_related_search_vectors(),
            [('alias__fts', 'simple_unaccent')]
        )

    def test_search_filters(self):
        """Assert that the queryset returned by search() has the expected filters."""
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
        config, value = query.get_source_expressions()
        self.assertEqual(value.value, "'''Hovercraft''':*")
        self.assertEqual(config.config.value, 'simple_unaccent')
        self.assertEqual(query.function, 'to_tsquery')

        self.assertIsInstance(stemmed, SearchVectorExact)
        col, query = stemmed.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        config, value = query.get_source_expressions()
        self.assertEqual(value.value, "Hovercraft")
        self.assertEqual(config.config.value, 'german_unaccent')
        self.assertEqual(query.function, 'plainto_tsquery')

        self.assertIsInstance(related, SearchVectorExact)
        col, query = related.get_source_expressions()
        self.assertEqual(col.target, self.alias_opts.get_field('fts'))
        self.assertIsInstance(query, SearchQuery)
        config, value = query.get_source_expressions()
        self.assertEqual(value.value, "'''Hovercraft''':*")
        self.assertEqual(config.config.value, 'simple_unaccent')
        self.assertEqual(query.function, 'to_tsquery')

    def test_search_rank_annotation(self):
        """
        Assert that the queryset returned by search() has the expected rank
        annotation.
        """
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
        col, query, *_ = simple.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        config, value = query.get_source_expressions()
        # Both config and value are Value expressions:
        self.assertEqual(value.value, "'''Hovercraft''':*")
        self.assertEqual(config.config.value, 'simple_unaccent')
        self.assertEqual(query.function, 'to_tsquery')

        # 'stemmed' should be the search rank with the stemmed search query
        self.assertIsInstance(stemmed, SearchRank)
        col, query, *_ = stemmed.get_source_expressions()
        self.assertEqual(col.target, self.opts.get_field('svf'))
        self.assertIsInstance(query, SearchQuery)
        config, value = query.get_source_expressions()
        self.assertEqual(value.value, "Hovercraft")
        self.assertEqual(config.config.value, 'german_unaccent')
        self.assertEqual(query.function, 'plainto_tsquery')

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
        col, query, *_ = related.get_source_expressions()
        self.assertEqual(col.target, self.alias_opts.get_field('fts'))
        self.assertIsInstance(query, SearchQuery)
        config, value = query.get_source_expressions()
        self.assertEqual(value.value, "'''Hovercraft''':*")
        self.assertEqual(config.config.value, 'simple_unaccent')
        self.assertEqual(query.function, 'to_tsquery')

    def test_search_rank_annotation_related_rank_only(self):
        """
        Assert that only the rank for the related vectors appears in the
        query annotations if no model rank could be built (f.ex. when the
        search vector feld was missing columns).
        """
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
            col, query, *_ = search_rank.get_source_expressions()
            self.assertEqual(col.target, self.alias_opts.get_field('fts'))

    def test_search_rank_annotation_model_rank_only(self):
        """
        Assert that only the rank for the model field appears in the
        query annotations if no related rank could be built.
        """
        mocked_get_related = Mock(return_value={})
        with patch.object(self.queryset, '_get_related_search_vectors', mocked_get_related):
            queryset = self.queryset.search('Hovercraft')
            self.assertIn('rank', queryset.query.annotations)
            rank = queryset.query.annotations['rank']
            # the rank expression should be the combined expression for the two
            # columns of the model's search vector field
            self.assertIsInstance(rank, CombinedExpression)
            for expr in rank.get_source_expressions():
                col, query, *_ = expr.get_source_expressions()
                self.assertEqual(col.target, self.opts.get_field('svf'))

    def test_search_no_columns_no_related_vectors(self):
        """
        Assert that no filters or annotations are added to the queryset if no
        columns and no related search vectors were declared.
        """
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
        """
        Assert that an empty (using none()) queryset is returned if no search
        term was provided.
        """
        queryset = self.queryset.search('')
        self.assertEqual(len(queryset.query.where.children), 1)
        self.assertIsInstance(queryset.query.where.children[0], NothingNode)
        self.assertFalse(queryset.query.annotations)


class TestProvenienzSearch(DataTestCase):
    """
    Performing a text search on the Provenienz model raised an error, due to
    an invalid `name_field`. The name_field was `geber`. When adding ordering
    to the result queryset of the search, TextSearchQuerySetMixin was adding
    ordering items with 'iexact' and 'istartswith' lookups, which are invalid on
    the field `geber` (it being a relation field).
    """

    model = _models.Provenienz

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, geber__name="Foo Bar")
        super().setUpTestData()

    def test_search(self):
        self.assertIn(self.obj, self.model.objects.search("Foo Bar"))
