from django import forms
from mizdb_tomselect.widgets import MIZSelect, MIZSelectMultiple

from dbentry.site.forms import InlineForm, MIZEditForm
from dbentry.site.widgets import MIZURLInput
from tests.case import MIZTestCase
from tests.test_site.models import Band


class BandEditForm(MIZEditForm):
    class Meta(InlineForm.Meta):
        model = Band
        fields = forms.ALL_FIELDS


class BandInlineForm(InlineForm):
    class Meta(InlineForm.Meta):
        model = Band
        fields = forms.ALL_FIELDS


class TestEditForm(MIZTestCase):
    form = BandEditForm

    def m2m_field(self):
        """Return the form's formfield for the M2M model field."""
        return self.form.base_fields["genres"]

    def fk_field(self):
        """Return the form's formfield for the FK model field."""
        return self.form.base_fields["origin"]

    def url_field(self):
        """Return the form's formfield for the URL model field."""
        return self.form.base_fields["url"]

    def test_m2m_field_widget(self):
        """Assert that the default widget for an M2M field is a MIZSelectMultiple."""
        self.assertIsInstance(self.m2m_field().widget, MIZSelectMultiple)

    def test_m2m_field_not_required(self):
        """Assert that the formfield for an M2M field is not required."""
        self.assertFalse(self.m2m_field().required)

    def test_fk_field_widget(self):
        """Assert that the default widget for a FK field is a MIZSelect."""
        self.assertIsInstance(self.fk_field().widget, MIZSelect)

    def test_fk_field_empty_label(self):
        """Assert that the formfield for a FK field has no empty label."""
        self.assertIsNone(self.fk_field().empty_label)

    def test_url_field_widget(self):
        """Assert that the default widget for a URL field is a MIZURLInput."""
        self.assertIsInstance(self.url_field().widget, MIZURLInput)


class TestInlineForm(MIZTestCase):
    form = BandInlineForm

    def m2m_field(self):
        """Return the form's formfield for the M2M model field."""
        return self.form.base_fields["genres"]

    def fk_field(self):
        """Return the form's formfield for the FK model field."""
        return self.form.base_fields["origin"]

    def url_field(self):
        """Return the form's formfield for the URL model field."""
        return self.form.base_fields["url"]

    def test_m2m_field_widget(self):
        """Assert that the default widget for an M2M field is a MIZSelectMultiple."""
        self.assertIsInstance(self.m2m_field().widget, MIZSelectMultiple)

    def test_m2m_field_not_required(self):
        """Assert that the formfield for an M2M field is not required."""
        self.assertFalse(self.m2m_field().required)

    def test_fk_field_widget(self):
        """Assert that the default widget for a FK field is a MIZSelect."""
        self.assertIsInstance(self.fk_field().widget, MIZSelect)

    def test_fk_field_empty_label(self):
        """Assert that the formfield for a FK field has no empty label."""
        self.assertIsNone(self.fk_field().empty_label)

    def test_url_field_widget(self):
        """Assert that the default widget for a URL field is a MIZURLInput."""
        self.assertIsInstance(self.url_field().widget, MIZURLInput)
