from unittest.mock import Mock, patch

from tests.case import MIZTestCase

from dbentry.export.widgets import ChoiceLabelWidget, YesNoBooleanWidget


class TestYesNoBooleanWidget(MIZTestCase):
    def setUp(self):
        self.widget = YesNoBooleanWidget()

    def test_render_true(self):
        self.assertEqual(self.widget.render(value=True), "Ja")

    def test_render_false(self):
        self.assertEqual(self.widget.render(value=False), "Nein")

    def test_render_null_value(self):
        with patch.object(self.widget, "NULL_VALUES", [None]):
            self.assertEqual(self.widget.render(value=None), "")


class TestChoiceLabelWidget(MIZTestCase):
    def setUp(self):
        self.field_name = "foo"
        self.widget = ChoiceLabelWidget(field_name=self.field_name)

    def test_init_sets_field_name(self):
        self.assertEqual(self.widget.field_name, self.field_name)

    def test_render(self):
        mock_foo_display = Mock()
        mock_obj = Mock(get_foo_display=mock_foo_display)
        self.widget.render(value=None, obj=mock_obj)
        mock_foo_display.assert_called()

    @patch("dbentry.export.widgets.super")
    def test_render_no_foo_display(self, super_mock):
        """
        Render should call the super method if the given object does not have a
        get_foo_display attribute.
        """
        mock_obj = Mock(spec=object, spec_set=True)
        self.widget.render("bar", mock_obj)
        super_mock.assert_called()

    @patch("dbentry.export.widgets.super")
    def test_render_foo_display_not_callable(self, super_mock):
        """
        Render should call the super method if the get_foo_display attribute of
        the given object is not callable.
        """
        mock_obj = Mock(get_foo_display="")
        self.widget.render("bar", mock_obj)
        super_mock.assert_called()
