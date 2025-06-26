from unittest.mock import Mock, patch

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from import_export.fields import Field

from dbentry.export.base import MIZResource, get_verbose_name_for_resource_field
from dbentry.export.fields import AnnotationField
from dbentry.export.widgets import YesNoBooleanWidget
from tests.case import MIZTestCase


class DummyModel(models.Model):
    name_set = models.TextField(verbose_name="Verbose Name Explicitly Set")
    no_name_set = models.TextField()


class DummyResource(MIZResource):
    class Meta:
        model = DummyModel
        select_related = ["foo"]


class TestMIZResource(MIZTestCase):
    def setUp(self):
        super().setUp()
        self.resource = DummyResource()

    def test_filter_export_calls_defer_fts(self):
        mock_queryset = Mock()
        with patch.object(self.resource, "_defer_fts") as defer_fts_mock:
            self.resource.filter_export(mock_queryset)
            defer_fts_mock.assert_called()

    def test_filter_export_calls_add_annotations(self):
        mock_queryset = Mock()
        with patch.object(self.resource, "_add_annotations") as add_annotations_mock:
            self.resource.filter_export(mock_queryset)
            add_annotations_mock.assert_called()

    def test_filter_export_calls_select_related(self):
        mock_queryset = Mock()
        with patch.object(self.resource, "_select_related") as select_related_mock:
            self.resource.filter_export(mock_queryset)
            select_related_mock.assert_called()

    def test_filter_export_filters_by_pk(self):
        mock_queryset = Mock()
        pk_name = "foo"
        mock_queryset.model._meta.pk.name = pk_name
        order_by_mock = Mock()
        mock_queryset.order_by = order_by_mock
        with patch.object(self.resource, "_defer_fts", new=Mock(return_value=mock_queryset)):
            self.resource.filter_export(mock_queryset)
            order_by_mock.assert_called_with(pk_name)

    def test_add_annotations(self):
        mock_queryset = Mock()
        annotate_mock = Mock()
        mock_queryset.annotate = annotate_mock
        for add_annotations in (True, False):
            with self.subTest(add_annotations=add_annotations):
                self.resource.add_annotations = add_annotations
                self.resource._add_annotations(mock_queryset)
                if add_annotations:
                    annotate_mock.assert_called()
                else:
                    annotate_mock.assert_not_called()
                annotate_mock.reset_mock()

    def test_add_annotations_adds_annotations(self):
        mock_queryset = Mock()
        annotations = {"foo": models.Count("*")}
        annotate_mock = Mock()
        mock_queryset.annotate = annotate_mock
        with patch.object(self.resource, "get_annotations", new=Mock(return_value=annotations)):
            self.resource._add_annotations(mock_queryset)
            annotate_mock.assert_called_with(**annotations)

    def test_defer_fts(self):
        mock_queryset = Mock()
        defer_mock = Mock()
        mock_queryset.defer = defer_mock
        self.resource._defer_fts(mock_queryset)
        defer_mock.assert_called()

    def test_defer_fts_no_fts_field(self):
        mock_queryset = Mock()
        mock_queryset.model._meta.get_field.side_effect = FieldDoesNotExist()
        defer_mock = Mock()
        mock_queryset.defer = defer_mock
        self.resource._defer_fts(mock_queryset)
        defer_mock.assert_not_called()

    def test_select_related(self):
        mock_queryset = Mock()
        select_related = ["foo", "bar"]
        select_related_mock = Mock()
        mock_queryset.select_related = select_related_mock
        with patch.object(self.resource._meta, "select_related", new=select_related):
            self.resource._select_related(mock_queryset)
            select_related_mock.assert_called_with(*select_related)

    def test_select_related_no_select_related(self):
        mock_queryset = Mock()
        select_related_mock = Mock()
        mock_queryset.select_related = select_related_mock
        with patch.object(self.resource._meta, "select_related", new=[]):
            self.resource._select_related(mock_queryset)
            select_related_mock.assert_not_called()

    def test_get_export_headers(self):
        """
        Assert that get_export_headers calls get_verbose_name_for_resource_field
        for every export field.
        """
        export_fields = [Mock(), Mock()]
        with patch("dbentry.export.base.get_verbose_name_for_resource_field") as get_verbose_mock:
            with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
                with patch.object(self.resource, "get_field_name"):
                    self.resource.get_export_headers()
        self.assertEqual(get_verbose_mock.call_count, len(export_fields))

    def test_get_annotations(self):
        export_fields = ["any", AnnotationField(attribute="foo", expr="bar")]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            self.assertEqual(self.resource.get_annotations(), {"foo": "bar"})

    def test_widget_from_django_field_boolean_field(self):
        field = models.BooleanField()
        self.assertEqual(MIZResource.widget_from_django_field(field), YesNoBooleanWidget)

    def test_widget_from_django_field_null_boolean_field(self):
        field = models.NullBooleanField()
        self.assertEqual(MIZResource.widget_from_django_field(field), YesNoBooleanWidget)

    def test_widget_from_django_field_no_boolean_field(self):
        field = models.IntegerField()
        self.assertNotEqual(MIZResource.widget_from_django_field(field), YesNoBooleanWidget)


class TestGetVerboseName(MIZTestCase):
    def setUp(self):
        self.resource = DummyResource()

    def test_get_verbose_name_for_resource_field_column_name_set(self):
        """
        Assert that get_verbose_name_for_resource_field prioritizes an
        explicitly set column_name over other names.
        """
        field = Field(attribute="name_set", column_name="Explicit Column Name")
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=[field])):
            with patch.object(self.resource, "fields", new={"name_set": field}):
                self.assertEqual(get_verbose_name_for_resource_field(self.resource, "name_set"), "Explicit Column Name")

    def test_get_verbose_name_for_resource_field_model_verbose_name(self):
        """
        Assert that get_verbose_name_for_resource_field uses the verbose name
        defined on the model field if no explicit column_name is set.
        """
        field = Field(attribute="name_set", column_name="name_set")
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=[field])):
            with patch.object(self.resource, "fields", new={"name_set": field}):
                self.assertEqual(
                    get_verbose_name_for_resource_field(self.resource, "name_set"), "Verbose Name Explicitly Set"
                )

    def test_get_verbose_name_for_resource_field_derived_verbose_name(self):
        """
        Assert that get_verbose_name_for_resource_field capitalizes the first
        letter of a model field verbose name that has been derived from the
        model field's name because no explicit verbose name was set.
        """
        field = Field(attribute="no_name_set")
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=[field])):
            with patch.object(self.resource, "fields", new={"no_name_set": field}):
                self.assertEqual(get_verbose_name_for_resource_field(self.resource, "no_name_set"), "No name set")

    def test_get_verbose_name_for_resource_field_no_model_field_column_name(self):
        """
        Assert that get_verbose_name_for_resource_field uses the field's name
        if no model field could be found and no explicit column name was set.
        """
        field = Field(attribute="does_not_exist")
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=[field])):
            with patch.object(self.resource, "fields", new={"does_not_exist": field}):
                self.assertEqual(get_verbose_name_for_resource_field(self.resource, "does_not_exist"), "Does not exist")

    def test_get_verbose_name_for_resource_field_no_resource_field(self):
        """
        Assert that get_verbose_name_for_resource_field raises a ValueError if
        the resource does not have a field with the given name.
        """

        def test_callable():
            return get_verbose_name_for_resource_field(self.resource, "foo")

        self.assertRaises(ValueError, test_callable)
