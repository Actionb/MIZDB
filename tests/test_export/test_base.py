from unittest.mock import Mock, patch

from django.core.exceptions import FieldDoesNotExist
from django.db import models
from import_export.fields import Field

from dbentry.export.base import MIZResource
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
        Assert that get_export_headers prefers the value given by the
        column_name argument if column_name isn't the default value (which
        would be equal to the value of the attribute argument).
        """
        export_fields = [Field(attribute="name_set", column_name="bar")]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            self.assertEqual(self.resource.get_export_headers(), ["bar"])

    def test_get_export_headers_model_field_verbose_name(self):
        """
        Assert that get_export_headers uses the field's verbose name if
        column_name has the default value (equal to attribute argument).
        """
        export_fields = [Field(attribute="name_set", column_name="name_set")]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            self.assertEqual(self.resource.get_export_headers(), ["Verbose Name Explicitly Set"])

    def test_get_export_headers_not_a_model_field(self):
        export_fields = [Field(attribute="not_on_model", column_name="A Different Field")]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert self.resource.get_export_headers() == ["A Different Field"]

    def test_get_export_headers_column_name_is_none(self):
        """
        Assert that get_export_headers uses the field's verbose name if the
        value for the column_name argument is None.
        """
        export_fields = [Field(attribute="name_set", column_name=None)]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            self.assertEqual(self.resource.get_export_headers(), ["Verbose Name Explicitly Set"])

    def test_get_export_headers_capitalizes_derived_verbose_name(self):
        """
        Assert that get_export_headers capitalizes a verbose name that has been
        derived from the model field's name.
        """
        export_fields = [Field(attribute="no_name_set")]
        with patch.object(self.resource, "get_export_fields", new=Mock(return_value=export_fields)):
            self.assertEqual(self.resource.get_export_headers(), ["No name set"])

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
