from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from import_export.fields import Field

from dbentry.export.base import MIZResource
from dbentry.export.fields import AnnotationField
from dbentry.export.widgets import YesNoBooleanWidget


class DummyModel(models.Model):
    foo = models.TextField(verbose_name="Foo")


class DummyResource(MIZResource):
    class Meta:
        model = DummyModel
        select_related = ["foo"]


@pytest.fixture
def mock_queryset():
    return Mock()


class TestMIZResource:
    @pytest.fixture
    def resource(self):
        return DummyResource()

    def test_filter_export_calls_defer_fts(self, resource, mock_queryset):
        with patch.object(resource, "_defer_fts") as defer_fts_mock:
            resource.filter_export(mock_queryset)
            defer_fts_mock.assert_called()

    def test_filter_export_calls_add_annotations(self, resource, mock_queryset):
        with patch.object(resource, "_add_annotations") as add_annotations_mock:
            resource.filter_export(mock_queryset)
            add_annotations_mock.assert_called()

    def test_filter_export_calls_select_related(self, resource, mock_queryset):
        with patch.object(resource, "_select_related") as select_related_mock:
            resource.filter_export(mock_queryset)
            select_related_mock.assert_called()

    def test_filter_export_filters_by_pk(self, resource, mock_queryset):
        pk_name = "foo"
        mock_queryset.model._meta.pk.name = pk_name
        order_by_mock = Mock()
        mock_queryset.order_by = order_by_mock
        with patch.object(resource, "_defer_fts", new=Mock(return_value=mock_queryset)):
            resource.filter_export(mock_queryset)
            order_by_mock.assert_called_with(pk_name)

    @pytest.mark.parametrize("add_annotations", [True, False])
    def test_add_annotations(self, resource, mock_queryset, add_annotations):
        annotate_mock = Mock()
        mock_queryset.annotate = annotate_mock
        resource.add_annotations = add_annotations
        resource._add_annotations(mock_queryset)
        if add_annotations:
            annotate_mock.assert_called()
        else:
            annotate_mock.assert_not_called()
        annotate_mock.reset_mock()

    def test_add_annotations_adds_annotations(self, resource, mock_queryset):
        annotations = {"foo": models.Count("*")}
        annotate_mock = Mock()
        mock_queryset.annotate = annotate_mock
        with patch.object(resource, "get_annotations", new=Mock(return_value=annotations)):
            resource._add_annotations(mock_queryset)
            annotate_mock.assert_called_with(**annotations)

    def test_defer_fts(self, resource, mock_queryset):
        defer_mock = Mock()
        mock_queryset.defer = defer_mock
        resource._defer_fts(mock_queryset)
        defer_mock.assert_called()

    def test_defer_fts_no_fts_field(self, resource, mock_queryset):
        mock_queryset.model._meta.get_field.side_effect = FieldDoesNotExist()
        defer_mock = Mock()
        mock_queryset.defer = defer_mock
        resource._defer_fts(mock_queryset)
        defer_mock.assert_not_called()

    def test_select_related(self, resource, mock_queryset):
        select_related = ["foo", "bar"]
        select_related_mock = Mock()
        mock_queryset.select_related = select_related_mock
        with patch.object(resource._meta, "select_related", new=select_related):
            resource._select_related(mock_queryset)
            select_related_mock.assert_called_with(*select_related)

    def test_select_related_no_select_related(self, resource, mock_queryset):
        select_related_mock = Mock()
        mock_queryset.select_related = select_related_mock
        with patch.object(resource._meta, "select_related", new=[]):
            resource._select_related(mock_queryset)
            select_related_mock.assert_not_called()

    def test_get_export_headers(self, resource):
        export_fields = [Field(attribute="foo", column_name="bar")]
        with patch.object(resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert resource.get_export_headers() == ["bar"]

    def test_get_export_headers_model_field_verbose_name(self, resource):
        export_fields = [Field(attribute="foo", column_name="foo")]
        with patch.object(resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert resource.get_export_headers() == ["Foo"]

    def test_get_export_headers_not_a_model_field(self, resource):
        export_fields = [Field(attribute="not_on_model", column_name="A Different Field")]
        with patch.object(resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert resource.get_export_headers() == ["A Different Field"]

    def test_get_export_headers_column_name_is_none(self, resource):
        export_fields = [Field(attribute="foo")]
        with patch.object(resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert resource.get_export_headers() == ["Foo"]

    def test_get_annotations(self, resource):
        export_fields = ["any", AnnotationField(attribute="foo", expr="bar")]
        with patch.object(resource, "get_export_fields", new=Mock(return_value=export_fields)):
            assert resource.get_annotations() == {"foo": "bar"}

    def test_widget_from_django_field_boolean_field(self):
        field = models.BooleanField()
        assert MIZResource.widget_from_django_field(field) == YesNoBooleanWidget
        pass

    def test_widget_from_django_field_null_boolean_field(self):
        field = models.NullBooleanField()
        assert MIZResource.widget_from_django_field(field) == YesNoBooleanWidget

    def test_widget_from_django_field_no_boolean_field(self):
        field = models.IntegerField()
        assert MIZResource.widget_from_django_field(field) != YesNoBooleanWidget
