import json

from django import forms
from django.test import override_settings
from django.urls import path
from django.views.generic import FormView
from formset.widgets import Selectize

from dbentry.site.views.base import AutocompleteMixin
from tests.case import DataTestCase, ViewTestCase
from tests.model_factory import make
from tests.test_site.models import Band, Musician


class Form(forms.ModelForm):
    class Meta:
        model = Musician
        fields = forms.ALL_FIELDS
        widgets = {
            'band': Selectize(),
            'origin': Selectize()
        }


class AutocompleteTestView(AutocompleteMixin, FormView):
    form_class = Form
    template_name = "test_template.html"


class URLConf:
    urlpatterns = [
        path('', AutocompleteTestView.as_view(), name='test_autocomplete')
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestAutocomplete(ViewTestCase, DataTestCase):
    model = Band
    view_class = AutocompleteTestView

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, name="Black Rebel Motorcycle Club", alias="BRMC")
        cls.other = make(cls.model, name='Foo', alias='Bar')
        super().setUpTestData()

    def test_get(self):
        response = self.get_response('', data={'field': 'band', 'search': 'BRMC'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['options'], [{'id': self.obj.pk, 'label': str(self.obj)}])

    def test_get_no_search_term(self):
        response = self.get_response('', data={'field': 'band'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['count'], 2)

    def test_get_invalid_field(self):
        response = self.get_response('', data={'field': 'foobar', 'search': 'BRMC'})
        self.assertEqual(response.status_code, 400)

    def test_get_autocomplete_queryset(self):
        """
        Assert that the queryset of the requested autocomplete form field is
        returned.
        """
        view = self.get_view()
        request = self.get_request('', data={'field': 'band'})
        queryset = view.get_autocomplete_queryset(request)
        self.assertEqual(queryset.model, self.model)

    def test_get_autocomplete_queryset_widget(self):
        """
        Assert that get_autocomplete_queryset raises an AssertionError if the
        field's widget is not a Selectize or DualSelector instance.
        """
        view = self.get_view()
        request = self.get_request('', data={'field': 'name'})
        with self.assertRaises(AssertionError):
            view.get_autocomplete_queryset(request)

    def test_can_do_text_search(self):
        view = self.get_view()
        request = self.get_request('', data={'field': 'band', 'search': 'BRMC'})
        self.assertTrue(view.can_do_text_search(request))

    def test_can_do_text_search_no_search_term(self):
        """
        can_do_text_search should return False if the request did not contain a
        search term.
        """
        view = self.get_view()
        for search_data in ({}, {'search': ''}):
            with self.subTest(search=search_data):
                request = self.get_request('', data={'field': 'band', **search_data})
                self.assertFalse(view.can_do_text_search(request))

    def test_can_do_text_search_text_search_not_supported(self):
        """
        can_do_text_search should return False if the queryset does not support
        text search.
        """
        view = self.get_view()
        request = self.get_request('', data={'field': 'origin', 'search': 'BRMC'})
        self.assertFalse(view.can_do_text_search(request))

    def test_view_uses_text_search(self):
        """
        Assert that the autocomplete view uses the queryset's text search
        function.
        """
        ...
