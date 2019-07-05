from ..base import AdminTestCase

from unittest import mock
from urllib.parse import urlparse

from django.http.request import QueryDict
from django.utils.http import urlencode
from django.urls import reverse

from DBentry import models as _models, admin as _admin
from DBentry.fields import PartialDate
from DBentry.factory import batch, make

class TestAdminMixin(AdminTestCase):
    
    model = _models.bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    
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
            with self.subTest(key=key, value=value):
                self.assertIn(key, kwargs)
                self.assertEqual(kwargs[key], value)
                
    def test_search_form_added_to_response_context(self):
        # Assert that the changelist_view's response context contains 'advanced_search_form'.
        response = self.client.get(path = self.changelist_path)
        self.assertIn('advanced_search_form', response.context)
        self.assertIn('search_var', response.context)
    
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
        # Assert that lookups defined on the search form are generally allowed.
        self.model_admin.search_form_kwargs = {'fields': ['genre__genre']}
        self.model_admin.get_search_form()
        self.assertTrue(self.model_admin.lookup_allowed('genre__genre', None))
        # genre__genre is a CharField, implicitly including the icontains lookup
        self.model_admin.search_form.lookups['genre__genre'] = ['icontains']
        msg = "Registered lookup 'icontains' for genre__genre should be allowed."
        self.assertTrue(self.model_admin.lookup_allowed('genre__genre__icontains', None), msg = msg) 
        msg = "Lookup 'year' for genre__genre is not registered"\
            " on the search_form's lookup mapping and thus should not be allowed."
        self.assertFalse(self.model_admin.lookup_allowed('genre__genre__year', None), msg = msg)
        
    def test_response_post_save_preserves_multi_values(self):
        # Assert that multiple values of a preserved_filter querystring are included in the redirect url
        # back to the changelist from the changeform.
        # (they were dropped previously due to calling dict() on a MultiValueDict-esque collection.)
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        request = self.get_request(path = self.change_path.format(pk = obj.pk), data = request_data)
        redirect = self.model_admin._response_post_save(request, obj)
        query_string = urlparse(redirect.url)[4]
        self.assertEqual(
            sorted(QueryDict(query_string).lists()), 
            sorted(QueryDict('genre=1&genre=2').lists())
        )        
        
    def test_response_post_save_returns_index_on_noperms(self):
        # Assert that _response_post_save returns the default response (the index)
        # when leaving a changeform with a post request while not having view or change perms.
        obj = make(self.model)
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        request = self.get_request(
            path = self.change_path.format(pk = obj.pk), data = request_data, 
            user = self.noperms_user
        )
        redirect = self.model_admin._response_post_save(request, obj)
        self.assertEqual(redirect.url, reverse('admin:index'))
        
    def test_preserved_filters_back_to_cl(self):
        # Assert that saving on a changeform returns back to the changelist 
        # with the filters preserved.
        # This is a more integrated test for the changes made in _reponse_post_save.
        preserved_filters_name = '_changelist_filters'
        obj = make(self.model)
        filters = [
            ('single_date', {'datum_0': '2019-05-19'}), 
            ('date_range', {'datum_0': '2019-05-19', 'datum_1': '2019-05-20'}), 
            ('fk', {'reihe': '1'}),    
            ('m2m', {'genre': ['1', '2']}),
        ]
        # disable the inlines so we do not have to provide all the post data for them
        with mock.patch.object(_admin.BildmaterialAdmin, 'inlines', []):
            for filter_type, filter in filters:
                changelist_filters = urlencode(filter, doseq = True)
                preserved_filters = urlencode({preserved_filters_name: changelist_filters})
                with self.subTest(filter_type=filter_type):
                    response = self.client.post(
                        path = self.change_path.format(pk = obj.pk) + '?' + preserved_filters, 
                        data = {'_save': True, 'titel': 'irrelevant'}, 
                        follow = True
                    )
                    request = response.wsgi_request
                    self.assertEqual(response.status_code, 200)
                    # Compare the querystring of the request with the original changelist_filters
                    query_string = urlparse(request.get_full_path())[4]
                    self.assertEqual(
                        sorted(QueryDict(query_string).lists()), 
                        sorted(QueryDict(changelist_filters).lists())
                    )
                    # Check that the request contains the data necessary to restore
                    # the filters.
                    for lookup, value in filter.items():
                        with self.subTest(lookup = lookup):
                            self.assertIn(lookup, request.GET)
                            if isinstance(value, list):
                                self.assertEqual(request.GET.getlist(lookup), value)
                            else:
                                self.assertEqual(request.GET[lookup], value)
                            
class TestSearchFormChangelist(AdminTestCase):
    
    model = _models.bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    
    search_form_kwargs = {
        'fields': [
            'titel',  # text
            'datum__range', # partial date + range
            'genre',  # m2m
            'reihe',  # FK
        ]
    }
    
    @classmethod
    def setUpTestData(cls):
        cls.genre1, cls.genre2 = batch(_models.genre, 2)
        cls.reihe = make(_models.Bildreihe)
        cls.test_data = [
            make(
                _models.bildmaterial, titel = 'Object1', datum = '2019-05-19', 
                genre = [cls.genre1, cls.genre2]
            ), 
            make(
                _models.bildmaterial, titel = 'Object2',  datum = '2019-05-20', 
                genre = [cls.genre1]
            ), 
            make(
                _models.bildmaterial, titel = 'Object3',  datum = '2019-05-21', 
                reihe = cls.reihe, 
            ), 
        ]
        super().setUpTestData()
        
    def test_changelist(self):
        # Assert that the changelist can be created without errors.
        response = self.client.get(self.changelist_path)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 3)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_titel(self):
        # icontains = 'object' should find all three
        request_data = {'titel': 'object'}
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 3)
        # icontains = 'object1' should only find obj1
        request_data['titel'] = 'object1'
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj1, changelist.result_list)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range(self):
        request_data = {
            'datum_0_0':2019, 'datum_0_1': 5, 'datum_0_2': 19, 
            'datum_1_0':2019, 'datum_1_1': 5, 'datum_1_2': 20
        }
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range_no_end(self):
        request_data = {'datum_0_0':2019, 'datum_0_1': 5, 'datum_0_2': 19, }
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj1, changelist.result_list)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range_no_start(self):
        request_data = {'datum_1_0':2019, 'datum_1_1': 5, 'datum_1_2': 20}
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_genre(self):
        request_data = {'genre': [self.genre1.pk, self.genre2.pk]}
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_reihe(self):
        request_data = {'reihe': self.reihe.pk}
        response = self.client.get(path = self.changelist_path, data = request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj3, changelist.result_list)
        
    def test_get_filters_params_select_multiple_lookup(self):
        # Assert that the params returned contain a valid lookup (i.e. '__in' for SelectMultiple).
        form_data = {'genre': [self.genre1.pk, self.genre2.pk]}
        self.model_admin.search_form_kwargs = {'fields': ['genre']}
        request = self.get_request(path = self.changelist_path, data = form_data)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params()
        self.assertIn('genre__in', params)
        self.assertEqual(params['genre__in'], '%s,%s' % (self.genre1.pk, self.genre2.pk))
        
    def test_get_filters_params_range_lookup(self):
        # Assert that the params returned contain a valid lookup (i.e. '__range' for RangeFormField).
        form_data = {
            'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, 
            'datum_1_0':2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
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
        form_data = {
            'datum_1_0':2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum__lte', params)
        self.assertEqual(params['datum__lte'], PartialDate(2020, 5, 22))
        
    def test_get_filters_params_range_lookup_no_end(self):
        # Assert that the params returned contain a valid lookup (i.e. '__range' for RangeFormField).
        # __range without end specified => exact lookup
        form_data = {
            'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, 
        }
        self.model_admin.search_form_kwargs = {'fields': ['datum__range']}
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], PartialDate(2020, 5, 20))
        
    def test_get_filters_params_multifield(self):
        # Check how changelist copes with MultiValueFields such as PartialDateFormField:
        # the changelist must query with the cleaned data only and not the indiviual fields.
        form_data = {'datum_0':2020, 'datum_1': 5, 'datum_2': 20}
        self.model_admin.search_form_kwargs = {'fields': ['datum']}
        request = self.get_request(path = self.changelist_path)
        changelist = self.get_changelist(request)
        
        expected = PartialDate(2020, 5, 20)
        params = changelist.get_filters_params(form_data)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], expected)
        for key in form_data:
            with self.subTest():
                self.assertNotIn(key, params)
        
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_preserved_filters_result_list(self):
        # Assert that all items of the result list have the preserved filters attached to the link.
        preserved_filters_name = '_changelist_filters'
        filters = [
            ('single_date', {'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, }), 
            ('date_range', {
                'datum_0_0':2020, 'datum_0_1': 5, 'datum_0_2': 20, 
                'datum_1_0':2020, 'datum_1_1': 5, 'datum_1_2': 22
            }), 
            ('fk', {'reihe': str(self.reihe.pk)}),    
            ('m2m', {'genre': [self.genre1.pk, self.genre2.pk]}),
        ]
        for filter_type, filter in filters:
            with self.subTest(filter_type = filter_type):
                response = self.client.get(path = self.changelist_path, data = filter)
                expected = urlencode({
                    preserved_filters_name: urlencode(filter)
                })
                for result in response.context['results']:
                    if 'href=' not in result:
                        continue
                    with self.subTest():
                        self.assertIn(expected, result)
                
    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)        
    def test_no_search_form_filtering_on_post(self):
        # Assert that no special filtering is being done on a POST request (i.e. actions)
        request = self.post_request(path = self.changelist_path + '?titel=NoFilter', data = {})
        cl = self.get_changelist(request)
        filters = cl.get_filters_params()
        self.assertFalse(filters)
        
