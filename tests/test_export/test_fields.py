from unittest.mock import Mock, patch

from dbentry.export.fields import AnnotationField, CachedQuerysetField, ChoiceField
from dbentry.export.widgets import ChoiceLabelWidget
from tests.case import MIZTestCase


class TestAnnotationField(MIZTestCase):
    def test_init_sets_expr(self):
        f = AnnotationField(expr="foo")
        self.assertEqual(f.expr, "foo")


class TestCachedQuerysetField(MIZTestCase):
    def setUp(self):
        self.pk_name = "id"
        self.attribute = "foo"

    def test_init_sets_queryset(self):
        f = CachedQuerysetField(queryset="foo")
        self.assertEqual(f.queryset, "foo")

    def test_cache_builds_dict_from_queryset(self):
        mock_model_meta = Mock()
        mock_model_meta.pk = Mock()  # 'name' is a kwarg for Mock, so can't set pk.name here
        mock_model_meta.pk.name = self.pk_name
        mock_model = Mock()
        mock_model._meta = mock_model_meta
        mock_queryset = Mock(model=mock_model)

        mock_queryset.values.return_value = [{self.pk_name: "1", self.attribute: "bar"}]
        f = CachedQuerysetField(attribute=self.attribute, queryset=mock_queryset)
        self.assertEqual(f.cache, {"1": {self.attribute: "bar"}})

    def test_export_returns_cached_value(self):
        f = CachedQuerysetField(attribute=self.attribute)
        mock_obj = Mock(pk="1")
        with patch("dbentry.export.fields.CachedQuerysetField.cache", new={"1": {self.attribute: "bar"}}):
            self.assertEqual(f.export(mock_obj), "bar")

    def test_export_no_value(self):
        f = CachedQuerysetField(attribute=self.attribute)
        mock_obj = Mock(pk="1")
        with patch("dbentry.export.fields.CachedQuerysetField.cache", new={"1": {}}):
            self.assertEqual(f.export(mock_obj), "")


class TestChoiceField(MIZTestCase):
    def test_init_sets_widget_if_widget_is_none(self):
        f = ChoiceField(attribute="foo", widget=None)
        self.assertIsInstance(f.widget, ChoiceLabelWidget)
        self.assertEqual(f.widget.field_name, f.attribute)

    def test_init_does_not_set_widget_if_widget_is_not_none(self):
        f = ChoiceField(attribute="foo", widget="bar")
        self.assertNotIsInstance(f.widget, ChoiceLabelWidget)

    def test_init_does_not_set_widget_if_attribute_is_not_none(self):
        f = ChoiceField(attribute=None, widget=None)
        self.assertNotIsInstance(f.widget, ChoiceLabelWidget)
