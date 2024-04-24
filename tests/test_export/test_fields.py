from unittest.mock import Mock, patch

import pytest

from dbentry.export.fields import AnnotationField, CachedQuerysetField, ChoiceField
from dbentry.export.widgets import ChoiceLabelWidget


@pytest.fixture
def pk_name():
    return "id"


@pytest.fixture
def mock_model_meta(pk_name):
    meta = Mock()
    meta.pk = Mock()  # 'name' is a kwarg for Mock, so can't set pk.name here
    meta.pk.name = pk_name
    return meta


@pytest.fixture
def mock_model(mock_model_meta):
    model = Mock()
    model._meta = mock_model_meta
    return model


@pytest.fixture
def mock_queryset(mock_model):
    return Mock(model=mock_model)


@pytest.fixture
def attribute():
    return "foo"


class TestAnnotationField:
    def test_init_sets_expr(self):
        f = AnnotationField(expr="foo")
        assert f.expr == "foo"


class TestCachedQuerysetField:
    def test_init_sets_queryset(self):
        f = CachedQuerysetField(queryset="foo")
        assert f.queryset == "foo"

    def test_cache_builds_dict_from_queryset(self, mock_queryset, pk_name):
        attribute = "foo"
        mock_queryset.values.return_value = [{pk_name: "1", attribute: "bar"}]
        f = CachedQuerysetField(attribute=attribute, queryset=mock_queryset)
        assert f.cache == {"1": {attribute: "bar"}}

    def test_export_returns_cached_value(self, mock_queryset):
        f = CachedQuerysetField(attribute=attribute)
        mock_obj = Mock(pk="1")
        with patch("dbentry.export.fields.CachedQuerysetField.cache", new={"1": {attribute: "bar"}}):
            assert f.export(mock_obj) == "bar"

    def test_export_no_value(self):
        f = CachedQuerysetField(attribute=attribute)
        mock_obj = Mock(pk="1")
        with patch("dbentry.export.fields.CachedQuerysetField.cache", new={"1": {}}):
            assert f.export(mock_obj) == ""


class TestChoiceField:
    def test_init_sets_widget_if_widget_is_none(self):
        f = ChoiceField(attribute="foo", widget=None)
        assert isinstance(f.widget, ChoiceLabelWidget)
        assert f.widget.field_name == f.attribute

    def test_init_does_not_set_widget_if_widget_is_not_none(self):
        f = ChoiceField(attribute="foo", widget="bar")
        assert not isinstance(f.widget, ChoiceLabelWidget)

    def test_init_does_not_set_widget_if_attribute_is_not_none(self):
        f = ChoiceField(attribute=None, widget=None)
        assert not isinstance(f.widget, ChoiceLabelWidget)
