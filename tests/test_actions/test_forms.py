from django.test import TestCase

from dbentry.actions.forms import BrochureActionFormOptions


class TestBrochureActionFormOptions(TestCase):
    form_class = BrochureActionFormOptions

    def test_init_disables_delete_magazin_field(self):
        """
        Assert that the 'delete_magazin' field is disabled, if
        'can_delete_magazin' argument is False.
        """
        for can_delete in (True, False):
            with self.subTest(can_delete=can_delete):
                form = self.form_class(can_delete_magazin=can_delete)
                self.assertEqual(form.fields['delete_magazin'].disabled, not can_delete)
