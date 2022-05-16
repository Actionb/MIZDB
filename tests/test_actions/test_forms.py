from django.core.exceptions import ValidationError

from dbentry import models as _models
from dbentry.actions.forms import BrochureActionFormOptions
from dbentry.tests.base import FormTestCase


class TestBrochureActionFormOptions(FormTestCase):

    form_class = BrochureActionFormOptions

    def test_clean_brochure_art(self):
        form = self.get_form()
        form.cleaned_data = {'brochure_art': 'INVALID'}
        with self.assertRaises(ValidationError):
            form.clean_brochure_art()

        form.cleaned_data['brochure_art'] = 'Katalog'
        with self.assertNotRaises(ValidationError):
            form.clean_brochure_art()

    def test_brochure_art_choices(self):
        form = self.get_form()
        choices = form.fields['brochure_art'].choices
        self.assertEqual(len(choices), 3)
        expected_choices = [
            (_models.Brochure._meta.model_name, _models.Brochure._meta.verbose_name),
            (_models.Katalog._meta.model_name, _models.Katalog._meta.verbose_name),
            (_models.Kalender._meta.model_name, _models.Kalender._meta.verbose_name)
        ]
        for value, label in expected_choices:
            with self.subTest(value=value, label=label):
                self.assertIn((value, label), choices)
