from django.test import TestCase
from django.urls import reverse

from dbentry.actions.forms import BrochureActionFormOptions, ReplaceForm
from tests.case import DataTestCase
from tests.model_factory import make
from tests.test_actions.models import Band, Genre


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
                self.assertEqual(form.fields["delete_magazin"].disabled, not can_delete)


class TestReplaceForm(DataTestCase):
    model = Genre
    form_class = ReplaceForm

    @classmethod
    def setUpTestData(cls):
        cls.genre1 = make(Genre)
        cls.genre2 = make(Genre)
        super().setUpTestData()

    def test_valid(self):
        form = self.form_class(
            data={"replacements": [str(self.genre1.pk), str(self.genre2.pk)]},
            choices={"replacements": self.model.objects.all()},
        )
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_init_sets_widget_verbose_name(self):
        """Assert that the widget's verbose_name attribute is set during init."""
        for model in (Band, Genre):
            with self.subTest(model=model):
                form = self.form_class(choices={"replacements": model.objects.all()})
                self.assertEqual(form.fields["replacements"].widget.verbose_name, model._meta.verbose_name_plural)

    def test_media_includes_jsi18n(self):
        """
        Assert that the form's media includes the jsi18n package required by
        the FilteredSelectMultiple widget.
        """
        form = self.form_class(choices={"replacements": self.model.objects.all()})
        self.assertIn(reverse("admin:jsi18n"), form.media._js)
