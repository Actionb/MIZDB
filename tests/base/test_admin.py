from unittest.mock import patch
from django.test import TestCase

from dbentry.base.admin import AutocompleteMixin

# TODO: don't forget to re-check this test module!!

class TestAutocompleteMixin(TestCase):

    class DummyModelField:
        name = 'dummy'
        related_model = 'anything'

    def test_formfield_for_foreignkey(self):
        """
        formfield_for_foreignkey should call make_widget with tabular=True, if
        the field's name is in the inline's 'tabular_autocomplete' list.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = ['dummy']
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)

                make_mock.assert_called()
                _args, kwargs = make_mock.call_args
                self.assertIn('tabular', kwargs)
                self.assertTrue(kwargs['tabular'])

    def test_formfield_for_foreignkey_no_tabular(self):
        """
        formfield_for_foreignkey should call make_widget with tabular=False, if
        the field's name isn't present in the 'tabular_autocomplete' list.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                inline.formfield_for_foreignkey(db_field=self.DummyModelField(), request=None)

                make_mock.assert_called()
                _args, kwargs = make_mock.call_args
                self.assertIn('tabular', kwargs)
                self.assertFalse(kwargs['tabular'])

    def test_formfield_for_foreignkey_no_override(self):
        """
        formfield_for_foreignkey should not call make_widget, if a widget was
        passed in.
        """
        with patch('dbentry.base.admin.super'):
            with patch('dbentry.base.admin.make_widget') as make_mock:
                inline = AutocompleteMixin()
                inline.tabular_autocomplete = []
                inline.formfield_for_foreignkey(
                    db_field=self.DummyModelField(), request=None, widget=object
                )
                make_mock.assert_not_called()
