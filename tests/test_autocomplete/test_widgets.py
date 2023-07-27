from mizdb_tomselect.widgets import MIZSelect, MIZSelectTabular, MIZSelectTabularMultiple, MIZSelectMultiple

from dbentry.autocomplete.widgets import make_widget
from tests.case import MIZTestCase
from tests.test_autocomplete.models import Ausgabe


class TestMakeWidget(MIZTestCase):
    model = Ausgabe

    def test_make_widget(self):
        self.assertIsInstance(make_widget(self.model, tabular=False), MIZSelect)

    def test_make_widget_tabular(self):
        self.assertIsInstance(make_widget(self.model, tabular=True), MIZSelectTabular)

    def test_make_widget_select_multiple(self):
        self.assertIsInstance(make_widget(self.model, tabular=False, multiple=True), MIZSelectMultiple)

    def test_make_widget_tabular_select_multiple(self):
        self.assertIsInstance(make_widget(self.model, tabular=True, multiple=True), MIZSelectTabularMultiple)

    def test_make_widget_takes_widget_class(self):
        """make_widget should return a widget of the passed in widget_class."""

        class DummyWidget(MIZSelect):
            pass

        widget = make_widget(self.model, widget_class=DummyWidget)
        self.assertIsInstance(widget, DummyWidget)

    def test_make_widget_sets_value_field(self):
        """Assert that make_widget sets a default for "value_field"."""
        widget = make_widget(self.model)
        self.assertEqual(widget.value_field, self.model._meta.pk.name)

    def test_make_widget_sets_label_field(self):
        """Assert that make_widget sets a default for "label_field"."""
        widget = make_widget(self.model)
        self.assertEqual(widget.label_field, self.model.name_field)

    def test_make_widget_sets_search_lookup(self):
        """Assert that make_widget sets a default for "search_lookup"."""
        widget = make_widget(self.model)
        self.assertEqual(widget.search_lookup, f"{self.model.name_field}__icontains")

    def test_make_widget_sets_create_field(self):
        """Assert that make_widget sets a default for "create_field"."""
        widget = make_widget(self.model)
        self.assertEqual(widget.create_field, self.model.create_field)

    def test_make_widget_sets_label_field_label(self):
        """Assert that make_widget sets a default for "label_field_label"."""
        widget = make_widget(self.model, tabular=True)
        self.assertEqual(widget.label_field_label, Ausgabe._meta.verbose_name)

    def test_make_widget_sets_placeholder(self):
        """Assert that make_widget sets a placeholder if filter_by is provided."""
        widget = make_widget(self.model, filter_by=("magazin", "magazin_id"))
        self.assertEqual(widget.attrs["placeholder"], "Bitte zuerst Magazin auswählen.")

    def test_make_widget_sets_add_url(self):
        """Assert that make_widget sets the add_url."""
        for can_add in (True, False):
            with self.subTest(can_add=can_add):
                widget = make_widget(self.model, can_add=can_add)
                if can_add:
                    self.assertEqual(
                        widget.add_url, f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_add"
                    )
                else:
                    self.assertFalse(widget.add_url)

    def test_make_widget_sets_changelist_url(self):
        """Assert that make_widget sets the changelist_url."""
        for can_list in (True, False):
            with self.subTest(can_list=can_list):
                widget = make_widget(self.model, can_list=can_list)
                if can_list:
                    self.assertEqual(
                        widget.changelist_url,
                        f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist",
                    )
                else:
                    self.assertFalse(widget.changelist_url)

    def test_make_widget_sets_edit_url(self):
        """Assert that make_widget sets the edit_url."""
        for can_edit in (True, False):
            with self.subTest(can_edit=can_edit):
                widget = make_widget(self.model, can_edit=can_edit)
                if can_edit:
                    self.assertEqual(
                        widget.edit_url, f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change"
                    )
                else:
                    self.assertFalse(widget.edit_url)

    def test_make_widget_url_namespace(self):
        """Assert that make_widget adds urls with a given namespace."""
        for namespace in ("", "foo"):
            with self.subTest(namespace=namespace):
                widget = make_widget(self.model, namespace=namespace)
                if namespace:
                    self.assertTrue(widget.add_url.startswith(f"{namespace}:"))
                else:
                    self.assertTrue(
                        widget.add_url.startswith(f"{self.model._meta.app_label}_{self.model._meta.model_name}")
                    )
