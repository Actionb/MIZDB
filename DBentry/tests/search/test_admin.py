from ..base import MyTestCase, AdminTestCase

from unittest import mock

from django import forms

from DBentry import models as _models, admin as _admin
from DBentry.search.admin import AdminSearchFormMixin, ChangelistSearchFormMixin
from DBentry.fields import PartialDate

class TestAdminMixin(AdminTestCase):
    
    model = _models.bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    
    def setUp(self):
        super().setUp()
        # Check if model_admin_class inherits from AdminSearchFormMixin.
        # setUp() isn't quite the right place to do it (setUp runs for every test),
        # but I couldn't be bothered.
        msg = "'%s' does not inherit from '%s'" % (
            self.model_admin_class.__name__, AdminSearchFormMixin.__name__)
        self.assertIsInstance(self.model_admin, AdminSearchFormMixin, msg = msg)
    
    @mock.patch('DBentry.search.admin.searchform_factory')
    def test_get_search_form_class(self, mocked_factory):
        # Test that a custom search_form_class is prioritized:
        self.model_admin.search_form_class = 1
        self.assertEqual(self.model_admin.get_search_form_class(), 1)
        
        # Test the default way:
        self.model_admin.search_form_class = None
        self.model_admin.search_form_kwargs = {'fields': 'datum'}
        self.model_admin.get_search_form_class(labels ={'datum': 'Das Datum!'})
        self.assertTrue(mocked_factory.called)
        args, kwargs = mocked_factory.call_args
        expected = {'fields': 'datum', 'labels': {'datum': 'Das Datum!'}}
        for key, value in expected.items():
            with self.subTest():
                self.assertIn(key, kwargs)
                self.assertEqual(kwargs[key], value)
            
    def test_get_search_form_with_wrapper(self):
        # Assert that the search form is wrapped in a wrapper declared by search_form_wrapper attribute.
        def dummy_wrapper(form):
            setattr(form, 'formwaswrapped', True)
            return form
        
        with mock.patch.object(self.model_admin, 'get_search_form_class') as mocked_form_class:
            mocked_form_class.return_value = type('Dummy', (forms.Form, ), {})
            self.model_admin.search_form_wrapper = dummy_wrapper
            form = self.model_admin.get_search_form()
            self.assertTrue(hasattr(form, 'formwaswrapped'))        
    
    def test_search_form_added_to_response_context(self):
        # Assert that the changelist_view's response context contains 'advanced_search_form'.
        response = self.client.get(path = self.changelist_path)
        self.assertIn('advanced_search_form', response.context)
        self.assertIn(SEARCH_VAR, response.context)
    
    def test_context_updated_with_form_media(self):
        # Assert that the context for the response contains the form's media.
        self.model_admin.search_form_kwargs = {'fields': ['datum']}
        response = self.client.get(path = self.changelist_path)
        self.assertIn('media', response.context)
        media = response.context['media']
        expected_js = ['admin/js/remove_empty_fields.js', 'admin/js/collapse.js']
        for javascript in expected_js:
            with self.subTest():
                self.assertIn(javascript, media._js)
        expected_css = [('all', 'admin/css/forms.css')]
        for group, css in expected_css:
            with self.subTest():
                self.assertIn(group, media._css)
                self.assertIn(css, media._css[group])
                
    def test_lookup_allowed(self):
        self.model_admin.search_form_kwargs = {'fields': ['genre__genre']}
        self.model_admin.get_search_form()
        self.assertTrue(self.model_admin.lookup_allowed('genre__genre', None))
        self.model_admin.search_form.lookups['genre__genre'] = ['icontains']
        msg = "Registered lookup 'icontains' for genre__genre should be allowed."
        self.assertTrue(self.model_admin.lookup_allowed('genre__genre__icontains', None), msg = msg) 
        msg = "Lookup 'icontains' for genre__genre is not registered"\
            " on the search_form's lookup mapping and thus should not be allowed."
        self.assertFalse(self.model_admin.lookup_allowed('genre__genre__year', None), msg = msg)

class TestSearchFormChangelist(AdminTestCase):
    # Tests without heavy mocking.
    
    model = _models.bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    def test_get_filters_params_select_multiple_lookup(self):
        # Assert that the params returned contain a valid lookup (i.e. '__in' for SelectMultiple).
        g1 = _models.genre.objects.create(genre='Beep')
        g2 = _models.genre.objects.create(genre='Boop')
        form_data = {'genre': [g1, g2]}
        self.model_admin.search_form_kwargs = {'fields': ['genre']}
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertIn('genre__in', params)
        self.assertEqual(list(params['genre__in']), [g1, g2])
        
    def test_get_filters_params_range_lookup(self):
        # Assert that the params returned contain a valid lookup (i.e. '__range' for RangeFormField).
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
        form_data = {
            'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, 
            'datum_1_0':2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertIn('datum__range', params)
        self.assertEqual(len(params['datum__range']), 2)
        start, end = params['datum__range']
        self.assertEqual(start, PartialDate(2020, 5, 20))
        self.assertEqual(end, PartialDate(2020, 5, 22))
        
    def test_get_filters_params_range_lookup_no_start(self):
        # Assert that the params returned contain a valid lookup (i.e. '__range' for RangeFormField).
        # __range without start specified => lte lookup
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
        form_data = {
            'datum_1_0':2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum__lte', params)
        self.assertEqual(params['datum__lte'], PartialDate(2020, 5, 22))
        
    def test_get_filters_params_range_lookup_no_end(self):
        # Assert that the params returned contain a valid lookup (i.e. '__range' for RangeFormField).
        # __range without end specified => exact lookup
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
        form_data = {
            'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, 
        }
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], PartialDate(2020, 5, 20))
        
    def test_changelist_query(self):
        # Using the filter params, assert that the changelist displays the correct 
        # queryset results.
        pass
        
    def test_get_filters_params_multifield(self):
        # Check how changelist copes with MultiValueFields such as PartialDateFormField:
        # the changelist must query with the cleaned data only and not the indiviual fields.
        self.model_admin.search_form_kwargs = {'fields': ['datum']}
        form_data = {'datum_0':2020, 'datum_1': 5, 'datum_2': 20}
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        
        expected = PartialDate(2020, 5, 20)
        params = changelist.get_filters_params(form_data)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], expected)
        for key in form_data:
            with self.subTest():
                self.assertNotIn(key, params)
