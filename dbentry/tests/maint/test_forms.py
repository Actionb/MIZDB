from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

import dbentry.models as _models
from dbentry.maint.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm,
    get_dupe_field_choices
)
from dbentry.sites import miz_site
from dbentry.tests.base import MyTestCase


class TestGetDupeFieldChoices(MyTestCase):

    def test_select_choices(self):
        select, _display = get_dupe_field_choices(_models.Musiker)
        self.assertIn(('kuenstler_name', 'Künstlername'), select)

    def test_select_choices_do_not_include_blank_fields(self):
        """
        Assert that the choices for the 'select' field do not include fields
        that can be blank.
        """
        select, _display = get_dupe_field_choices(_models.Musiker)
        self.assertNotIn(('beschreibung', 'Beschreibung'), select)

    def test_select_choices_include_non_nullable_foreignkey(self):
        """
        Assert that the choices for the 'select' field include non-nullable
        ForeignKey fields.
        """
        select, _display = get_dupe_field_choices(_models.Ausgabe)
        self.assertIn(('magazin', 'Magazin'), select)

    def test_select_choices_do_not_include_nullable_foreignkey(self):
        """
        Assert that the choices for the 'select' field do not include nullable
        ForeignKey fields.
        """
        select, _display = get_dupe_field_choices(_models.Musiker)
        self.assertNotIn(('person', 'Person'), select)

    def test_display_choices(self):
        _select, display = get_dupe_field_choices(_models.Musiker)
        self.assertIn(('kuenstler_name', 'Künstlername'), display)
        self.assertIn(('beschreibung', 'Beschreibung'), display)
        self.assertNotIn(('id', 'Id'), display)

    def test_display_choices_include_concrete_m2m(self):
        """Assert that the choices for the 'display' field include concrete M2M fields."""
        _select, display = get_dupe_field_choices(_models.Musiker)
        self.assertIn(('genre__genre', 'Genre'), display)

    def test_display_choices_include_reverse_m2m(self):
        """Assert that the choices for the 'display' field include reverse M2M relations."""
        _select, display = get_dupe_field_choices(_models.Musiker)
        self.assertIn(('band__band_name', 'Band'), display)

    def test_display_choices_include_reverse_o2m(self):
        """
        Assert that the choices for the 'display' field include reverse one to
        many relations.
        """
        _select, display = get_dupe_field_choices(_models.Musiker)
        self.assertIn(('musikeralias__alias', 'Alias'), display)


class TestModelSelectForm(MyTestCase):
    form_class = ModelSelectForm

    def test_init_passes_model_select_choices(self):
        """Assert that the choices for the field 'model_select' are set."""
        form = self.form_class()
        form.fields['model_select'].choices = []
        with patch.object(form, 'get_model_list') as model_list_mock:
            model_list_mock.return_value = [('The', 'Models')]
            form.__init__()
            self.assertEqual(form.fields['model_select'].choices, [('The', 'Models')])

    def test_get_model_list_filters_out_non_app_models(self):
        """Assert that models not belonging to the given app are filtered out."""
        form = self.form_class(app_label='dbentry', admin_site=miz_site)
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            get_models_mock.return_value = [
                _models.Musiker,  # should be included
                User,
                ContentType,
            ]
            self.assertEqual(form.get_model_list(), [('musiker', 'Musiker')])

    def test_get_model_list_filters_out_non_registered_models(self):
        """Assert that models not registered with the given admin site are filtered out."""
        form = self.form_class(app_label='dbentry', admin_site=miz_site)
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            get_models_mock.return_value = [
                _models.Musiker,  # should be included
                _models.BaseBrochure,  # not registered with 'miz_site'
            ]
            self.assertEqual(form.get_model_list(), [('musiker', 'Musiker')])

    def test_get_model_list_sorted_by_verbose_name(self):
        """Assert that the model list is sorted by model verbose_name."""
        form = self.form_class()
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            with patch.object(form, 'get_model_filters', new=Mock(return_value=[])):
                get_models_mock.return_value = [_models.Musiker, _models.Band, _models.Kalender]
                self.assertEqual(
                    form.get_model_list(),
                    [('band', 'Band'), ('musiker', 'Musiker'), ('kalender', 'Programmheft')]
                )


class TestDuplicateFieldsSelectForm(MyTestCase):
    form_class = DuplicateFieldsSelectForm

    def test_init_sets_choices(self):
        """Assert that the choices for the three fields are set in init."""
        form = self.form_class(model=_models.Musiker)
        form['select'].choices = []
        form['display'].choices = []

        with patch('dbentry.maint.forms.get_dupe_field_choices') as m:
            m.return_value = [
                [('kuenstler_name', 'Künstlername')],
                [('kuenstler_name', 'Künstlername'), ('musikeralias__alias', 'Alias')]
            ]
            form.__init__(model=_models.Musiker)
            self.assertEqual(form.fields['select'].choices, [('kuenstler_name', 'Künstlername')])
            self.assertEqual(
                form.fields['display'].choices,
                [('kuenstler_name', 'Künstlername'), ('musikeralias__alias', 'Alias')]
            )
