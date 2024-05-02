from unittest.mock import Mock, patch

import pytest

from dbentry.export.widgets import ChoiceLabelWidget, YesNoBooleanWidget


class TestYesNoBooleanWidget:

    @pytest.fixture
    def widget(self):
        return YesNoBooleanWidget()

    def test_render_true(self, widget):
        assert widget.render(value=True) == "Ja"

    def test_render_false(self, widget):
        assert widget.render(value=False) == "Nein"

    def test_render_null_value(self, widget):
        with patch.object(widget, "NULL_VALUES", [None]):
            assert widget.render(value=None) == ""


class TestChoiceLabelWidget:

    @pytest.fixture
    def field_name(self):
        return "foo"

    @pytest.fixture
    def widget(self, field_name):
        return ChoiceLabelWidget(field_name=field_name)

    def test_init_sets_field_name(self, widget, field_name):
        assert widget.field_name == field_name

    def test_render(self, widget):
        mock_foo_display = Mock()
        mock_obj = Mock(get_foo_display=mock_foo_display)
        widget.render(value=None, obj=mock_obj)
        mock_foo_display.assert_called()

    @patch("dbentry.export.widgets.super")
    def test_render_no_foo_display(self, super_mock, widget):
        """
        Render should call the super method if the given object does not have a
        get_foo_display attribute.
        """
        mock_obj = Mock(spec=object, spec_set=True)
        widget.render("bar", mock_obj)
        super_mock.assert_called()

    @patch("dbentry.export.widgets.super")
    def test_render_foo_display_not_callable(self, super_mock, widget):
        """
        Render should call the super method if the get_foo_display attribute of
        the given object is not callable.
        """
        mock_obj = Mock(get_foo_display="")
        widget.render("bar", mock_obj)
        super_mock.assert_called()
