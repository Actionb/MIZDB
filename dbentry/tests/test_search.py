from django.test import TestCase

from dbentry import models as _models
from dbentry.factory import make
from dbentry.tests.base import DataTestCase
from dbentry.fts import fields


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
        }
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


class TestWeightedColumn(TestCase):

    def test_deconstruct(self):
        # Assert that the column is deconstructed with the correct path and
        # the correct column's language.
        column = fields.WeightedColumn('name', 'weight', language='german')
        name, args, kwargs = column.deconstruct()
        self.assertEqual(name, 'dbentry.fts.fields.WeightedColumn')
        self.assertIn(args, 'german')


class TestSearchVectorField(TestCase):

    def test_deconstruct(self):
        # Assert that the field is deconstructed with the correct path.
        field = fields.SearchVectorField()
        name, path, args, kwargs = field.deconstruct()
        self.assertEqual(path, 'dbentry.fts.fields.SearchVectorField')
