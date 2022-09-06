from unittest import mock
from unittest.mock import patch
from urllib.parse import urlparse

from django import forms
from django.contrib import admin
from django.contrib.admin.views.main import ALL_VAR
from django.core import checks
from django.http.request import QueryDict
from django.test import TestCase, override_settings
from django.urls import path, reverse
from django.utils.http import urlencode

from dbentry import models as _models, admin as _admin
from dbentry.factory import batch, make
from dbentry.fields import PartialDate
from dbentry.search.admin import AdminSearchFormMixin, MIZAdminSearchFormMixin
from dbentry.search.forms import MIZAdminSearchForm, searchform_factory

from tests.case import AdminTestCase
from tests.models import Band, Musiker, Genre


admin_site = admin.AdminSite(name='test')


@admin.register(Band, site=admin_site)
class BandAdmin(AdminSearchFormMixin, admin.ModelAdmin):

    search_form_kwargs = {
        'fields': ['genre', 'musiker'],
        # specify a widget class that doesn't require autocomplete views like
        # the default widget would:
        'widgets': {
            'genre': forms.widgets.SelectMultiple,
            'musiker': forms.widgets.SelectMultiple
        },
        # the changelist template expects a MIZAdminFormMixin form:
        'form': MIZAdminSearchForm
    }
    fields = ['band_name']


@admin.register(Musiker, site=admin_site)
class MusikerAdmin(MIZAdminSearchFormMixin, admin.ModelAdmin):

    search_form_kwargs = {'fields': ['kuenstler_name', 'genre']}


class URLConf:
    urlpatterns = [path('test_search/', admin_site.urls)]


@override_settings(ROOT_URLCONF=URLConf)
class TestAdminMixin(AdminTestCase):

    admin_site = admin_site
    model = Band
    model_admin_class = BandAdmin

    @classmethod
    def setUpTestData(cls):
        cls.genre1 = make(Genre)
        cls.genre2 = make(Genre)
        super().setUpTestData()

    def test_has_search_form(self):
        """
        Assert that has_search_form returns True, if the search_form_kwargs
        declare search fields.
        """
        test_data = [
            (None, False), ({}, False), ({'fields': []}, False),
            ({'fields': ['name']}, True)
        ]
        for search_form_kwargs, expected in test_data:
            with self.subTest(search_form_kwargs=search_form_kwargs):
                with mock.patch.object(self.model_admin, 'search_form_kwargs', search_form_kwargs):
                    self.assertEqual(self.model_admin.has_search_form(), expected)

    @mock.patch('dbentry.search.admin.searchform_factory')
    def test_get_search_form_class(self, factory_mock):
        """
        Assert that the searchform_factory is called with the expected kwargs.
        (search_form_kwargs declared on the ModelAdmin + the passed in kwargs)
        """
        search_form_kwargs = {'fields': 'datum'}
        labels = {'datum': 'Das Datum!'}
        with mock.patch.object(self.model_admin, 'search_form_kwargs', search_form_kwargs):
            self.model_admin.get_search_form_class(labels=labels)
            expected = {'labels': labels, **search_form_kwargs}
            factory_mock.assert_called_with(model=self.model, **expected)

    @mock.patch('dbentry.search.admin.searchform_factory')
    def test_get_search_form(self, factory_mock):
        """Assert that the form class is instantiated with the provided kwargs."""
        form_class_mock = mock.Mock()
        factory_mock.return_value = form_class_mock
        self.model_admin.get_search_form(beep='boop')
        form_class_mock.assert_called_with(beep='boop')

    def test_context_contains_form(self):
        """
        Assert that the changelist_view's response context contains the form and
        items required for the rendering of that form.
        """
        response = self.client.get(path=self.changelist_path)
        for item in ('advanced_search_form', 'search_var', 'show_result_count', 'cl'):
            with self.subTest(item=item):
                self.assertIn(item, response.context)

    def test_context_contains_media(self):
        """Assert that the context for the response contains the form's media."""
        response = self.client.get(path=self.changelist_path)
        self.assertIn('media', response.context)
        media = response.context['media']
        self.assertIn('admin/js/remove_empty_fields.js', media._js)
        self.assertIn('admin/js/collapse.js', media._js)
        self.assertIn('all', media._css)
        self.assertIn('admin/css/forms.css', media._css['all'])

    def test_lookup_allowed(self):
        """Assert that lookups defined on the search form are generally allowed."""
        field_path = 'bandalias__alias'
        with mock.patch.object(self.model_admin, 'search_form_kwargs', {'fields': [field_path]}):
            form = self.model_admin.get_search_form()  # set the search_form attribute
            self.assertTrue(self.model_admin.lookup_allowed(field_path, None))
            # Add a lookup to the registered lookups for the field:
            form.lookups[field_path] = ['icontains']
            self.assertTrue(
                self.model_admin.lookup_allowed(f'{field_path}__icontains', None),
                msg=f"Registered lookup 'icontains' for {field_path} should be allowed."
            )

    def test_lookup_not_allowed(self):
        """
        Assert that a lookup that isn't already a valid relational lookup is
        not allowed unless it is registered with the given formfield.
        """
        field_path = 'bandalias__alias'
        with mock.patch.object(self.model_admin, 'search_form_kwargs',  {'fields': [field_path]}):
            form = self.model_admin.get_search_form()  # set the search_form attribute
            form.lookups = {}
            self.assertFalse(
                self.model_admin.lookup_allowed(f'{field_path}__icontains', None),
                msg=f"Lookup 'icontains' for {field_path} is not registered on the "
                    "search_form's lookup mapping and thus should not be allowed."
            )

    def test_invalid_lookup_not_allowed(self):
        """
        Assert that invalid lookups for a given field are not allowed even if
        they are registered.
        """
        field_path = 'bandalias__alias'
        with mock.patch.object(self.model_admin, 'search_form_kwargs',  {'fields': [field_path]}):
            form = self.model_admin.get_search_form()  # set the search_form attribute
            form.lookups = {field_path: ['year']}
            self.assertFalse(
                self.model_admin.lookup_allowed(f'{field_path}__year', None),
                msg=f"Lookup 'year' is an invalid lookup for {field_path}"
            )

    def test_lookup_allowed_range_lte_valid(self):
        """
        Assert that for any search field declared with a range lookup, the 'lte'
        lookup is also regarded as valid.
        """
        model_admin = MusikerAdmin(Musiker, admin_site)
        field_path = 'musikeraudiom2m__audio__tracks'
        with patch.object(model_admin, 'search_form_kwargs', {'fields': [f"{field_path}__range"]}):
            model_admin.get_search_form()
            self.assertTrue(model_admin.lookup_allowed(f'{field_path}__lte', None))

    def test_get_changeform_initial_data(self):
        """
        Assert that data from the search form is added to a changeform's initial
        data (via the '_changelist_filters' query arg).
        """
        request_data = {'_changelist_filters': f'genre={self.genre1.pk}&genre={self.genre2.pk}'}
        response = self.client.get(path=self.add_path, data=request_data)
        initial = response.context['adminform'].form.initial
        self.assertIn('genre__in', initial)
        self.assertEqual(initial['genre__in'], f"{self.genre1.pk},{self.genre2.pk}")

    def test_response_post_save_preserves_multi_values(self):
        """
        Assert that multiple values of a preserved_filter querystring are
        included in the redirect url back to the changelist from the changeform.
        (they were dropped previously due to calling dict() on a MultiValueDict)
        """
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        # get_preserved_filters expects a request with a resolver_match
        # attribute set, so get the wsgi request from the response:
        response = self.client.get(
            path=self.change_path.format(pk=obj.pk),
            data=request_data
        )
        redirect = self.model_admin._response_post_save(response.wsgi_request, obj)
        query_string = urlparse(redirect.url)[4]
        self.assertEqual(
            sorted(QueryDict(query_string).lists()),
            sorted(QueryDict('genre=1&genre=2').lists())
        )

    def test_response_post_save_returns_index_on_noperms(self):
        """
        Assert that _response_post_save redirects to the index (like with
        django's implementation of response_post_save), if the user does not
        have view or change permissions.
        """
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        # get_preserved_filters expects a request with a resolver_match
        # attribute set, so get the wsgi request from the response:
        self.client.force_login(self.noperms_user)
        response = self.client.get(
            path=self.change_path.format(pk=obj.pk),
            data=request_data
        )
        redirect = self.model_admin._response_post_save(response.wsgi_request, obj)
        self.assertEqual(redirect.url, reverse('admin:index'))

    def test_preserved_filters_back_to_cl(self):
        """Assert that changelist filters are preserved."""
        obj = make(self.model)
        filter_kwargs = {'genre': [str(self.genre1.pk), str(self.genre2.pk)]}
        changelist_filters = urlencode(filter_kwargs, doseq=True)
        preserved_filters = urlencode({'_changelist_filters': changelist_filters})
        # Disable the inlines, so we do not have to provide post data for them:
        with mock.patch.object(self.model_admin_class, 'inlines', []):
            response = self.client.post(
                path=self.change_path.format(pk=obj.pk) + '?' + preserved_filters,
                data={'_save': True, 'band_name': 'irrelevant'},
                follow=True
            )
            self.assertEqual(response.status_code, 200)
            request = response.wsgi_request
            query_string = urlparse(request.get_full_path()).query
            self.assertEqual(query_string, changelist_filters)
            # Check that the request contains the data necessary to restore
            # the filters.
            for lookup, value in filter_kwargs.items():
                with self.subTest(lookup=lookup):
                    self.assertIn(lookup, request.GET)
                    if isinstance(value, list):
                        self.assertEqual(request.GET.getlist(lookup), value)
                    else:
                        self.assertEqual(request.GET[lookup], value)

    def test_update_changelist_context_no_context_data(self):
        """
        Assert that update_changelist_context only alters responses that have
        a context_data attribute.
        """
        self.assertIsNone(self.model_admin.update_changelist_context(response=None))

    def test_update_changelist_context_adds_media(self):
        """Assert that update_changelist_context adds search form media."""
        search_form = mock.Mock(media="dummy_media")
        with mock.patch.object(self.model_admin, 'search_form', search_form, create=True):
            for context_data in ({}, {'media': 'admin_media '}):
                had_context = bool(context_data)
                with self.subTest(context_data=context_data):
                    response_mock = mock.Mock(context_data=context_data)
                    response = self.model_admin.update_changelist_context(response_mock)
                    self.assertIn('media', response.context_data)
                    if had_context:
                        # If context already contains media, then the search
                        # form media should be added to it:
                        self.assertEqual(response.context_data['media'], 'admin_media dummy_media')
                    else:
                        self.assertEqual(response.context_data['media'], 'dummy_media')

    def test_update_changelist_context_adds_template_tag_items(self):
        """
        Assert that context items from django's default 'search form' tag are
        added if 'cl' is present in context_data.
        """
        tag_mock = mock.Mock(return_value={'cl': "extra from tag"})
        with mock.patch('dbentry.search.admin.search_form_tag_context', tag_mock):
            for context_data in ({}, {'cl': ''}):
                had_context = bool(context_data)
                with self.subTest(context_data=context_data):
                    response_mock = mock.Mock(context_data=context_data)
                    response = self.model_admin.update_changelist_context(response_mock)
                    if had_context:
                        tag_mock.assert_called()
                        self.assertEqual(response.context_data['cl'], "extra from tag")
                    else:
                        tag_mock.assert_not_called()

    def test_check_search_form_fields_unknown_fields(self):
        """
        Assert that _check_search_form_fields correctly handles search fields
        that either cannot be resolved to a model field.
        """
        # Patch get_model_fields to restrict the check to search fields
        # declared in search_form_kwargs.
        get_model_fields_mock = mock.Mock(return_value=[])
        with mock.patch('dbentry.search.admin.utils.get_model_fields', new=get_model_fields_mock):
            with mock.patch.object(self.model_admin, 'search_form_kwargs'):
                # A search field that doesn't exist:
                self.model_admin.search_form_kwargs = {'fields': ['BeepBoop']}
                errors = self.model_admin._check_search_form_fields()
                self.assertTrue(errors)
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], checks.Info)
                self.assertEqual(
                    errors[0].msg,
                    "Ignored search form field: 'BeepBoop'. "
                    "Band has no field named 'BeepBoop'"
                )

    def test_check_search_form_fields_invalid_lookup(self):
        """
        Assert that _check_search_form_fields correctly handles search fields
        that have an invalid lookup.
        """
        # Patch get_model_fields to restrict the check to search fields
        # declared in search_form_kwargs.
        get_model_fields_mock = mock.Mock(return_value=[])
        with mock.patch('dbentry.search.admin.utils.get_model_fields', new=get_model_fields_mock):
            with mock.patch.object(self.model_admin, 'search_form_kwargs'):
                # A valid search field with an invalid lookup:
                self.model_admin.search_form_kwargs = {'fields': ['band_name__beep']}
                errors = self.model_admin._check_search_form_fields()
                self.assertTrue(errors)
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], checks.Info)
                self.assertEqual(
                    errors[0].msg,
                    "Ignored search form field: 'band_name__beep'. "
                    "Invalid lookup: beep for CharField."
                )

    def test_check_search_form_fields_missing_fields(self):
        """
        Assert that _check_search_form_fields complains about missing search
        fields.
        """
        with mock.patch.object(self.model_admin, 'search_form_kwargs'):
            self.model_admin.search_form_kwargs = {'fields': ['musiker']}
            errors = self.model_admin._check_search_form_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Info)
            self.assertEqual(
                errors[0].msg,
                "Changelist search form is missing fields for relations:\n\t['genre']"
            )
            