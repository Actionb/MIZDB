from unittest.mock import patch

from django import forms
from mizdb_tomselect.widgets import MIZSelect, MIZSelectMultiple

from dbentry import models as _models
from dbentry.site.forms import AusgabeInlineForm, InlineForm, MIZEditForm
from dbentry.site.widgets import MIZURLInput
from tests.case import DataTestCase, MIZTestCase
from tests.model_factory import make
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


@patch.object(AusgabeInlineForm._meta, "model", new=_models.Ausgabe.audio.through)
class TestAusgabeInlineForm(DataTestCase):
    model = _models.Ausgabe.audio.through
    form_class = AusgabeInlineForm

    @classmethod
    def setUpTestData(cls):
        cls.ausgabe = ausgabe = make(_models.Ausgabe)
        cls.obj = make(_models.Audio, ausgabe=ausgabe)
        super().setUpTestData()

    def test_initial_ausgabe_magazin(self):
        """Assert that init adds initial data for the magazin."""
        for instance in (self.model.objects.first(), None):
            with self.subTest(instance=instance):
                form = self.form_class(instance=instance)
                if instance:
                    self.assertEqual(form.initial["ausgabe__magazin"], self.ausgabe.magazin)
                else:
                    self.assertFalse(form.initial.get("ausgabe__magazin", False))
