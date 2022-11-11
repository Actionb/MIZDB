from django.db import models
from django.test import TestCase

from dbentry.fts.fields import SearchVectorField, WeightedColumn


class TestWeightedColumn(TestCase):

    def test_weighted_column_deconstruct(self):
        """
        Assert that deconstruct returns the correct path and arguments for
        WeightedColumn.
        """
        column = WeightedColumn('titel', 'A', language='simple')
        path, args, kwargs = column.deconstruct()
        self.assertEqual(path, 'dbentry.fts.fields.WeightedColumn')
        self.assertEqual(args, ['titel', 'A', 'simple'])


class TestSearchVectorField(TestCase):

    def test_search_field_deconstruct(self):
        """
        Assert that deconstruct returns the correct path and arguments for
        SearchVectorField.
        """
        column = WeightedColumn('title', 'A', 'simple')
        field = SearchVectorField(
            columns=[column],
            blank=False, editable=True,  # inverted default arguments
        )

        class SearchVectorModel(models.Model):
            title = models.CharField(max_length=100)
            search_field = field

        _name, path, args, kwargs = SearchVectorModel._meta.get_field('search_field').deconstruct()
        self.assertEqual(_name, 'search_field')
        self.assertEqual(path, 'dbentry.fts.fields.SearchVectorField')
        self.assertFalse(args)
        self.assertEqual(kwargs['columns'], [column])
        self.assertFalse(kwargs['blank'])
        self.assertTrue(kwargs['editable'])

        # blank and editable should be omitted if the parameters are the
        # default values.
        field = SearchVectorField(columns=[column], blank=True, editable=False)
        _name, _path, _args, kwargs = field.deconstruct()
        self.assertEqual(path, 'dbentry.fts.fields.SearchVectorField')
        self.assertNotIn('blank', kwargs)
        self.assertNotIn('editable', kwargs)

    def test_check_language_attribute(self):
        """Assert that the check catches missing WeightedColumn languages."""
        field = SearchVectorField(
            columns=[
                WeightedColumn('Ham', 'A', language='simple'),
                WeightedColumn('Bacon', 'C', language=''),
            ]
        )
        errors = list(field._check_language_attributes(textual_columns=[]))
        self.assertEqual(len(errors), 1)
        self.assertEqual(
            errors[0].msg,
            "Language required for column WeightedColumn('Bacon', 'C', '')"
        )
        self.assertEqual(errors[0].obj, field)
