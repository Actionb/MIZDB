from django.test import TestCase

import tsvector_field

from dbentry.fts.fields import SearchVectorField, WeightedColumn


class TestSearchVectorField(TestCase):

    def test_weighted_column_deconstruct(self):
        # Assert that deconstructs returns the correct path and arguments for
        # WeightedColumn.
        column = WeightedColumn('titel', 'A', language='simple')
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

    def test_check_language_attribute(self):
        # Assert that the check catches missing WeightedColumn languages.
        field = SearchVectorField(
            columns=[
                WeightedColumn('Ham', 'A', language='simple'),
                WeightedColumn('Bacon', 'C', language=''),
                tsvector_field.WeightedColumn('Egg', 'D'),
            ]
        )
        errors = list(field._check_language_attributes(textual_columns=None))
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0].msg,
            "Language required for column WeightedColumn('Bacon', 'C', '')"
        )
        self.assertEqual(errors[0].obj, field)
