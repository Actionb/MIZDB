from django import forms
from django.contrib.admin.helpers import Fieldset

from dbentry.admin.forms import MIZAdminFormMixin
from tests.case import MIZTestCase


class TestMIZAdminFormMixin(MIZTestCase):
    class Form(MIZAdminFormMixin, forms.Form):
        first_name = forms.CharField()
        last_name = forms.CharField(required=True)

    def test_iter(self):
        """Assert that __iter__ returns Fieldset instances."""
        for fs in self.Form().__iter__():
            self.assertIsInstance(fs, Fieldset)

    def test_media_adds_collapse_js(self):
        """
        The form's media should contain collapse.js if any of the fieldsets
        have 'collapse' in their classes.
        """
        form = self.Form()
        form.fieldsets = (["Name", {"fields": ["first_name", "last_name"], "classes": ()}],)
        self.assertNotIn("admin/js/collapse.js", form.media._js)
        form.fieldsets = (["Name", {"fields": ["first_name", "last_name"], "classes": ("collapse",)}],)
        self.assertIn("admin/js/collapse.js", form.media._js)
