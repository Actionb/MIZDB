from django.test import TestCase

import tsvector_field

from dbentry.fts.fields import SearchVectorField, WeightedColumn


class TestSearchVectorField(TestCase):

    def test_weighted_column_deconstruct(self):
        # Assert that deconstructs returns the correct path and arguments for
        # WeightedColumn.
        column = WeightedColumn('titel', weight='A', config='simple')
        path, args, kwargs = column.deconstruct()
        self.assertEqual(path, 'dbentry.fts.fields.WeightedColumn')
        self.assertEqual(args, ['titel', 'A', 'simple'])

    def test_search_field_deconstruct(self):
        # Assert that deconstructs returns the correct path and arguments for
        # SearchVectorField.
        test_field = SearchVectorField(
            columns=['some_column'],
            blank=False, editable=True,  # inverted the default arguments
        )
        _name, path, args, kwargs = test_field.deconstruct()
        # self.assertEqual(name, 'test_field')
        self.assertEqual(path, 'dbentry.fts.fields.SearchVectorField')
        self.assertFalse(args)
        self.assertIn('columns', kwargs)
        self.assertEqual(kwargs['columns'], ['some_column'])
        self.assertIn('blank', kwargs)
        self.assertFalse(kwargs['blank'])
        self.assertIn('editable', kwargs)
        self.assertTrue(kwargs['editable'])

        # blank and editable should be omitted if the parameters are the
        # default values.
        test_field = SearchVectorField(
            columns=['some_column'],
            blank=True, editable=False,
        )
        _name, _path, _args, kwargs = test_field.deconstruct()
        # self.assertEqual(name, 'test_field')
        self.assertEqual(path, 'dbentry.fts.fields.SearchVectorField')
        self.assertIn('columns', kwargs)
        self.assertEqual(kwargs['columns'], ['some_column'])
        self.assertNotIn('blank', kwargs)
        self.assertNotIn('editable', kwargs)
