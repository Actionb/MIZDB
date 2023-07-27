from django.db import models
from django.test import TestCase

from dbentry.fts.fields import SearchVectorField, WeightedColumn


column = WeightedColumn("title", "A", "simple")


class SearchVectorModel(models.Model):
    title = models.CharField(max_length=100)
    search_field = SearchVectorField(columns=[column])


class TestWeightedColumn(TestCase):
    def test_weighted_column_deconstruct(self):
        """
        Assert that deconstruct returns the correct path and arguments for
        WeightedColumn.
        """
        path, args, _kwargs = WeightedColumn("titel", weight="A", config="simple").deconstruct()
        self.assertEqual(path, "dbentry.fts.fields.WeightedColumn")
        self.assertEqual(args, ["titel", "A", "simple"])


class TestSearchVectorField(TestCase):
    def test_init(self):
        """
        A SearchVectorField should always initialize with null=True, blank=True
        and editable=False.
        """
        f = SearchVectorField()
        self.assertTrue(f.null)
        self.assertTrue(f.blank)
        self.assertFalse(f.editable)

    def test_search_field_deconstruct(self):
        """
        Assert that deconstruct returns the correct path and arguments for
        SearchVectorField.
        """
        name, path, _args, kwargs = SearchVectorModel._meta.get_field("search_field").deconstruct()
        self.assertEqual(name, "search_field")
        self.assertEqual(path, "dbentry.fts.fields.SearchVectorField")
        self.assertEqual(kwargs["columns"], [column])
        self.assertTrue(kwargs["null"])
        self.assertTrue(kwargs["blank"])
        self.assertFalse(kwargs["editable"])
