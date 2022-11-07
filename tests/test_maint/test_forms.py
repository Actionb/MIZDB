from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.test import TestCase

from dbentry.maint.forms import (
    DuplicateFieldsSelectForm, ModelSelectForm,
    get_dupe_field_choices
)
from .admin import admin_site
from .models import Kalender, Musiker, Person, Unregistered


class ForeignKeyA(models.Model):
    pass


class ForeignKeyB(models.Model):
    pass


class ForwardM2M(models.Model):
    title = models.CharField(max_length=100)

    name_field = 'title'


class DupeModel(models.Model):
    name = models.CharField('The Name', max_length=100)
    blank_field = models.CharField('Blank Field', max_length=100, blank=True)
    non_nullable_fk = models.ForeignKey(
        ForeignKeyA, verbose_name='Non-Nullable FK', on_delete=models.CASCADE
    )
    nullable_fk = models.ForeignKey(
        ForeignKeyB, blank=True, null=True, verbose_name='Nullable Fk', on_delete=models.CASCADE
    )
    concrete_m2m = models.ManyToManyField(ForwardM2M, verbose_name='Concrete M2M')


class ReverseM2M(models.Model):
    title = models.CharField(max_length=100)
    related = models.ManyToManyField(DupeModel, related_name='reverse_m2m')

    name_field = 'title'

    class Meta:
        verbose_name = 'Reverse M2M'


class ReverseFK(models.Model):
    title = models.CharField(max_length=100)
    related = models.ForeignKey(DupeModel, on_delete=models.CASCADE, related_name='reverse_fk')

    class Meta:
        verbose_name = 'Reverse FK'


class TestGetDupeFieldChoices(TestCase):
    model = DupeModel

    def test_select_choices(self):
        select, _display = get_dupe_field_choices(self.model)
        self.assertIn(('name', 'The name'), select)

    def test_select_choices_do_not_include_blank_fields(self):
        """
        Assert that the choices for the 'select' field do not include fields
        that can be blank.
        """
        select, _display = get_dupe_field_choices(self.model)
        self.assertNotIn(('blank_field', 'Blank field'), select)

    def test_select_choices_include_non_nullable_foreignkey(self):
        """
        Assert that the choices for the 'select' field include non-nullable
        ForeignKey fields.
        """
        select, _display = get_dupe_field_choices(self.model)
        self.assertIn(('non_nullable_fk', 'Non-nullable fk'), select)

    def test_select_choices_do_not_include_nullable_foreignkey(self):
        """
        Assert that the choices for the 'select' field do not include nullable
        ForeignKey fields.
        """
        select, _display = get_dupe_field_choices(self.model)
        self.assertNotIn(('nullable_fk', 'Nullable Fk'), select)

    def test_display_choices(self):
        _select, display = get_dupe_field_choices(self.model)
        self.assertIn(('name', 'The name'), display)
        self.assertIn(('blank_field', 'Blank field'), display)
        self.assertNotIn(('id', 'Id'), display)

    def test_display_choices_include_concrete_m2m(self):
        """Assert that the choices for the 'display' field include concrete M2M fields."""
        _select, display = get_dupe_field_choices(self.model)
        self.assertIn(('concrete_m2m__title', 'Concrete m2m'), display)

    def test_display_choices_include_reverse_m2m(self):
        """Assert that the choices for the 'display' field include reverse M2M relations."""
        _select, display = get_dupe_field_choices(self.model)
        self.assertIn(('reverse_m2m__title', 'Reverse M2M'), display)

    def test_display_choices_include_reverse_o2m(self):
        """
        Assert that the choices for the 'display' field include reverse
        one-to-many relations.
        """
        _select, display = get_dupe_field_choices(self.model)
        self.assertIn(('reverse_fk__pk', 'Reverse FK'), display)


class TestModelSelectForm(TestCase):
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
        form = self.form_class(app_label="test_maint", admin_site=admin_site)
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            get_models_mock.return_value = [
                Musiker,  # should be included
                User,  # should be filtered out
                ContentType,  # should be filtered out
            ]
            self.assertEqual(form.get_model_list(), [('musiker', 'Musiker')])

    def test_get_model_list_filters_out_non_registered_models(self):
        """Assert that models not registered with the given admin site are filtered out."""
        form = self.form_class(app_label="test_maint", admin_site=admin_site)
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            get_models_mock.return_value = [
                Musiker,  # should be included
                Unregistered,  # not registered with 'site'
            ]
            self.assertEqual(form.get_model_list(), [('musiker', 'Musiker')])

    def test_get_model_list_sorted_by_verbose_name(self):
        """Assert that the model list is sorted by model verbose_name."""
        form = self.form_class()
        with patch('dbentry.maint.forms.apps.get_models') as get_models_mock:
            with patch.object(form, 'get_model_filters', new=Mock(return_value=[])):
                get_models_mock.return_value = [Person, Musiker, Kalender]
                self.assertEqual(
                    form.get_model_list(),
                    [('musiker', 'Musiker'), ('person', 'Person'), ('kalender', 'Programmheft')]
                )


class TestDuplicateFieldsSelectForm(TestCase):
    form_class = DuplicateFieldsSelectForm

    def test_init_sets_choices(self):
        """Assert that the choices for the three fields are set in init."""
        form = self.form_class(model=Musiker)
        form['select'].choices = []
        form['display'].choices = []

        with patch('dbentry.maint.forms.get_dupe_field_choices') as m:
            m.return_value = [
                [('kuenstler_name', 'Künstlername')],
                [('kuenstler_name', 'Künstlername'), ('musikeralias__alias', 'Alias')]
            ]
            form.__init__(model=Musiker)
            self.assertEqual(form.fields['select'].choices, [('kuenstler_name', 'Künstlername')])
            self.assertEqual(
                form.fields['display'].choices,
                [('kuenstler_name', 'Künstlername'), ('musikeralias__alias', 'Alias')]
            )
