from unittest import mock
from urllib.parse import urlparse

from django.contrib.admin.views.main import ALL_VAR
from django.core import checks
from django.http.request import QueryDict
from django.urls import reverse
from django.utils.http import urlencode

from dbentry import models as _models, admin as _admin
from dbentry.factory import batch, make
from dbentry.fields import PartialDate
from dbentry.tests.base import AdminTestCase


class TestAdminMixin(AdminTestCase):

    model = _models.Bildmaterial
    model_admin_class = _admin.BildmaterialAdmin

    @mock.patch('dbentry.search.admin.searchform_factory')
    def test_get_search_form_class(self, mocked_factory):
        # Assert that the searchform_factory is called with a combination of
        # the ModelAdmin's search_form_kwargs and the passed in kwargs.
        search_form_kwargs = {'fields': 'datum'}
        labels = {'datum': 'Das Datum!'}
        with mock.patch.object(
                self.model_admin, 'search_form_kwargs', search_form_kwargs):
            self.model_admin.get_search_form_class(labels=labels)
            self.assertTrue(mocked_factory.called)
            args, kwargs = mocked_factory.call_args
            expected = {'labels': labels, **search_form_kwargs}
            for key, value in expected.items():
                with self.subTest(key=key, value=value):
                    self.assertIn(key, kwargs)
                    self.assertEqual(kwargs[key], value)

    def test_search_form_added_to_response_context(self):
        # Assert that the changelist_view's response context contains
        # 'advanced_search_form'.
        response = self.client.get(path=self.changelist_path)
        self.assertIn('advanced_search_form', response.context)
        self.assertIn('search_var', response.context)

    @mock.patch.object(
        _admin.BildmaterialAdmin,
        'search_form_kwargs',
        {'fields': ['datum']}
    )
    def test_context_updated_with_form_media(self):
        # Assert that the context for the response contains the form's media.
        response = self.client.get(path=self.changelist_path)
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
        search_form_kwargs = {'fields': ['genre__genre']}
        with mock.patch.object(
                self.model_admin, 'search_form_kwargs', search_form_kwargs):
            # Call get_search_form to add the instance attribute 'form'.
            form = self.model_admin.get_search_form()
            self.assertTrue(
                self.model_admin.lookup_allowed('genre__genre', None)
            )
            # genre__genre is a CharField, implicitly including the icontains lookup.
            # Add the lookup to the registered lookups for genre__genre:
            form.lookups['genre__genre'] = ['icontains']
            self.assertTrue(
                self.model_admin.lookup_allowed('genre__genre__icontains', None),
                msg="Registered lookup 'icontains' for genre__genre should be allowed."
            )
            # An unregistered lookup should not be allowed.
            self.assertFalse(
                self.model_admin.lookup_allowed('genre__genre__year', None),
                msg="Lookup 'year' for genre__genre is not registered on the "
                "search_form's lookup mapping and thus should not be allowed."
            )

    def test_lookup_allowed_range_end(self):
        # Assert that for a given search field declared with the range lookup,
        # the lte lookup is also valid.
        model_admin = _admin.AusgabenAdmin(_models.Ausgabe, _admin.miz_site)
        model_admin.get_search_form()  # set the search_form attribute
        # While ausgabejahr__jahr can be found as a field on the search form,
        # only the 'range' lookup will be registered and thus lte would be
        # regarded as invalid.
        self.assertTrue(model_admin.lookup_allowed('ausgabejahr__jahr__lte', None))

    def test_response_post_save_preserves_multi_values(self):
        # Assert that multiple values of a preserved_filter querystring are
        # included in the redirect url back to the changelist from the changeform.
        # (they were dropped previously due to calling dict() on a MultiValueDict.)
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        request = self.get_request(
            path=self.change_path.format(pk=obj.pk),
            data=request_data
        )
        redirect = self.model_admin._response_post_save(request, obj)
        query_string = urlparse(redirect.url)[4]
        self.assertEqual(
            sorted(QueryDict(query_string).lists()),
            sorted(QueryDict('genre=1&genre=2').lists())
        )

    def test_response_post_save_returns_index_on_noperms(self):
        # Assert that _response_post_save returns the default response (the index)
        # when leaving a changeform with a post request while not having view or
        # change perms.
        obj = make(self.model)
        request_data = {'_changelist_filters': 'genre=1&genre=2'}
        obj = make(self.model)
        request = self.get_request(
            path=self.change_path.format(pk=obj.pk), data=request_data,
            user=self.noperms_user
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
            # datum_0_2=19&datum_0_1=05&datum_0_0=2019
            ('single_date', {'datum_0_0': '2019', 'datum_0_1': '5', 'datum_0_2': '19'}),
            ('date_range', {
                'datum_0_0': '2019', 'datum_0_1': '5', 'datum_0_2': '19',
                'datum_1_0': '2019', 'datum_1_1': '5', 'datum_1_2': '20'
            }),
            ('fk', {'reihe': '1'}),
            ('m2m', {'genre': ['1', '2']})
        ]
        # Disable the inlines so we do not have to provide all the post data for them:
        patcher = mock.patch.object(_admin.BildmaterialAdmin, 'inlines', [])
        patcher.start()
        for filter_type, filter_kwargs in filters:
            changelist_filters = urlencode(filter_kwargs, doseq=True)
            preserved_filters = urlencode({preserved_filters_name: changelist_filters})
            with self.subTest(filter_type=filter_type):
                response = self.client.post(
                    path=self.change_path.format(pk=obj.pk) + '?' + preserved_filters,
                    data={'_save': True, 'titel': 'irrelevant'},
                    follow=True
                )
                request = response.wsgi_request
                self.assertEqual(response.status_code, 200)
                # Compare the querystring of the request with the original changelist_filters.
                query_string = urlparse(request.get_full_path()).query
                self.assertEqual(
                    sorted(QueryDict(query_string).lists()),
                    sorted(QueryDict(changelist_filters).lists())
                )
                # Check that the request contains the data necessary to restore
                # the filters.
                for lookup, value in filter_kwargs.items():
                    with self.subTest(lookup=lookup):
                        self.assertIn(lookup, request.GET)
                        if isinstance(value, list):
                            self.assertEqual(request.GET.getlist(lookup), value)
                        else:
                            self.assertEqual(request.GET[lookup], value)
        patcher.stop()

    def test_get_changeform_initial_data(self):
        # Assert that data from the search form (via the '_changelist_filters'
        # query arg) is added to a changeform's initial data.
        request_data = {
            '_changelist_filters': 'datum_0_0=2019&datum_0_2=1&datum_0_1=1'
        }
        response = self.client.get(path=self.add_path, data=request_data)
        add_form = response.context['adminform'].form
        self.assertIn('datum', add_form.initial)
        expected = PartialDate(2019, 1, 1)
        self.assertEqual(add_form.initial['datum'], expected)

    def test_context_contains_search_form_tag_items(self):
        # Assert that context variables usually added by django's search_form
        # tag are also included in a changelist template that uses the
        # advanced_search_form.
        vars_added_by_tag = ['show_result_count', 'search_var']
        response = self.client.get(path=self.changelist_path)
        for var in vars_added_by_tag:
            with self.subTest(var=var):
                # response.context contains a LOT of stuff;
                # assertIn would take up the entire screen should it fail.
                self.assertTrue(var in response.context)

    def test_update_changelist_context_checks_response_context_data(self):
        # Assert that update_changelist_context checks that the response has
        # the attribute 'context_data':
        self.assertIsNone(
            self.model_admin.update_changelist_context(response=None),
            msg="update_changelist_context should return any response object "
            "that does not have the attribute 'context_data'."
        )
        search_form = mock.Mock(media="dummy_media")
        patcher = mock.patch.object(
            _admin.BildmaterialAdmin, 'search_form', search_form, create=True)
        patcher.start()

        # Assert that a missing 'media' key in context_data is handled:
        response = self.model_admin.update_changelist_context(
            response=mock.Mock(context_data={}))
        self.assertIn(
            'media', response.context_data,
            msg="update_changelist_context should add a media entry if it was"
            " missing."
        )
        self.assertEqual(
            response.context_data['media'], self.model_admin.search_form.media,
            msg="update_changelist_context should add the search form's media"
            " to the response's context."
        )

        # Assert that the search_form's media is ADDED to the media already
        # present in context_data.
        response = self.model_admin.update_changelist_context(
            response=mock.Mock(context_data={'media': 'This is '}))
        self.assertIn(
            'media', response.context_data,
            msg="update_changelist_context should add a media entry if it was"
            " missing."
        )
        self.assertEqual(
            response.context_data['media'], "This is dummy_media",
            msg="update_changelist_context should add the search form's media"
            " to the response's context."
        )
        patcher.stop()

        # Assert that context items from django's default search form tag are
        # added if 'cl' is present in context_data.
        mocked_tag = mock.Mock(return_value={'cl': "extra from tag"})
        patcher = mock.patch(
            'dbentry.search.admin.search_form_tag_context', mocked_tag)
        patcher.start()
        response = self.model_admin.update_changelist_context(
            response=mock.Mock(context_data={}))
        self.assertFalse(
            mocked_tag.called,
            msg=(
                "search_form tag should only be called if context_data has "
                "the 'cl' key."
            )
        )
        response = self.model_admin.update_changelist_context(
            response=mock.Mock(context_data={'cl': ""}))
        self.assertTrue(mocked_tag.called)
        self.assertEqual(response.context_data['cl'], "extra from tag")
        patcher.stop()

    def test_check_search_form_fields(self):
        # Assert that _check_search_form_fields correctly ignores search fields
        # that cannot be resolved to a model field.
        # patch get_model_fields so the returned error list does not contain
        # items pertaining to missing search fields:
        patcher = mock.patch(
            'dbentry.search.admin.utils.get_model_fields', new=mock.Mock(return_value=[]))
        patcher.start()
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
                "Bildmaterial has no field named 'BeepBoop'"
            )
            # A valid search field with an invalid lookup:
            self.model_admin.search_form_kwargs = {'fields': ['titel__beep']}
            errors = self.model_admin._check_search_form_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Info)
            self.assertEqual(
                errors[0].msg,
                "Ignored search form field: 'titel__beep'. "
                "Invalid lookup: beep for CharField."
            )
        patcher.stop()

    def test_check_search_form_fields_missing_fields(self):
        # Assert that _check_search_form_fields complains about missing search
        # fields.
        patch_config = {
            'target': 'dbentry.search.admin.utils.get_model_fields',
            'new': mock.Mock(
                return_value=[
                    self.model._meta.get_field('genre'),
                    self.model._meta.get_field('schlagwort')
                ]
            )
        }
        with mock.patch(**patch_config):
            with mock.patch.object(self.model_admin, 'search_form_kwargs'):
                self.model_admin.search_form_kwargs = {'fields': ['schlagwort']}
                errors = self.model_admin._check_search_form_fields()
                self.assertTrue(errors)
                self.assertEqual(len(errors), 1)
                self.assertIsInstance(errors[0], checks.Info)
                self.assertEqual(
                    errors[0].msg,
                    "Changelist search form is missing fields for relations:\n\t['genre']"
                )

class TestSearchFormChangelist(AdminTestCase):

    model = _models.Bildmaterial
    model_admin_class = _admin.BildmaterialAdmin

    search_form_kwargs = {
        'fields': [
            'titel',  # text
            'datum__range',  # partial date + range
            'genre',  # m2m
            'reihe',  # FK
            'id__in',  # primary key
        ]
    }

    @classmethod
    def setUpTestData(cls):
        cls.genre1, cls.genre2 = batch(_models.Genre, 2)
        cls.reihe = make(_models.Bildreihe)
        cls.test_data = [
            make(
                _models.Bildmaterial, titel='Object1', datum='2019-05-19',
                genre=[cls.genre1, cls.genre2]
            ),
            make(
                _models.Bildmaterial, titel='Object2',  datum='2019-05-20',
                genre=[cls.genre1]
            ),
            make(
                _models.Bildmaterial, titel='Object3',  datum='2019-05-21',
                reihe=cls.reihe,
            ),
        ]
        super().setUpTestData()

    def test_changelist(self):
        # Assert that the changelist can be created without errors.
        response = self.client.get(self.changelist_path, data={ALL_VAR: ''})
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 3)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_titel(self):
        request_data = {'titel': 'Object1'}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj1, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range(self):
        request_data = {
            'datum_0_0': 2019, 'datum_0_1': 5, 'datum_0_2': 19,
            'datum_1_0': 2019, 'datum_1_1': 5, 'datum_1_2': 20
        }
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range_no_end(self):
        request_data = {'datum_0_0': 2019, 'datum_0_1': 5, 'datum_0_2': 19}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj1, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_datum_range_no_start(self):
        request_data = {'datum_1_0': 2019, 'datum_1_1': 5, 'datum_1_2': 20}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_genre(self):
        request_data = {'genre': [self.genre1.pk, self.genre2.pk]}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_reihe(self):
        request_data = {'reihe': self.reihe.pk}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 1)
        self.assertIn(self.obj3, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_filter_by_id(self):
        request_data = {'id': [",".join(str(pk) for pk in [self.obj1.pk, self.obj2.pk])]}
        response = self.client.get(path=self.changelist_path, data=request_data)
        self.assertEqual(response.status_code, 200)
        changelist = response.context['cl']
        self.assertEqual(len(changelist.result_list), 2, msg=changelist.result_list)
        self.assertIn(self.obj1, changelist.result_list)
        self.assertIn(self.obj2, changelist.result_list)

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_get_filters_params_select_multiple_lookup(self):
        # Assert that the params returned contain a valid lookup:
        # i.e. '__in' for SelectMultiple.
        form_data = {'genre': [self.genre1.pk, self.genre2.pk]}
        request = self.get_request(path=self.changelist_path, data=form_data)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params()
        self.assertIn('genre__in', params)
        self.assertEqual(
            params['genre__in'],
            '%s,%s' % (self.genre1.pk, self.genre2.pk)
        )

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_get_filters_params_range_lookup(self):
        # Assert that the params returned contain a valid lookup:
        # i.e. '__range' for RangeFormField.
        form_data = {
            'datum_0_0': 2020, 'datum_0_1': 5, 'datum_0_2': 20,
            'datum_1_0': 2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        request = self.get_request(path=self.changelist_path, data=form_data)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertIn('datum__range', params)
        self.assertEqual(len(params['datum__range']), 2)
        start, end = params['datum__range']
        self.assertEqual(start, PartialDate(2020, 5, 20))
        self.assertEqual(end, PartialDate(2020, 5, 22))

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_get_filters_params_range_lookup_no_start(self):
        # Assert that the params returned contain a valid lookup:
        # i.e. '__range' for RangeFormField.
        # __range without start specified => lte lookup
        form_data = {
            'datum_1_0': 2020, 'datum_1_1': 5, 'datum_1_2': 22
        }
        request = self.get_request(path=self.changelist_path, data=form_data)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum__lte', params)
        self.assertEqual(params['datum__lte'], PartialDate(2020, 5, 22))

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_get_filters_params_range_lookup_no_end(self):
        # Assert that the params returned contain a valid lookup:
        # i.e. '__range' for RangeFormField.
        # __range without end specified => exact lookup
        form_data = {
            'datum_0_0': 2020, 'datum_0_1': 5, 'datum_0_2': 20,
        }
        request = self.get_request(path=self.changelist_path, data=form_data)
        changelist = self.get_changelist(request)
        params = changelist.get_filters_params(form_data)
        self.assertNotIn('datum__range', params)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], PartialDate(2020, 5, 20))

    def test_get_filters_params_multifield(self):
        # Check how changelist copes with MultiValueFields such as PartialDateFormField:
        # the changelist must query with the cleaned data only and not the indiviual fields.
        form_data = {'datum_0': 2020, 'datum_1': 5, 'datum_2': 20}
        patcher = mock.patch.object(
            _admin.BildmaterialAdmin, 'search_form_kwargs', {'fields': ['datum']}
        )
        patcher.start()
        request = self.get_request(path=self.changelist_path, data=form_data)
        changelist = self.get_changelist(request)

        expected = PartialDate(2020, 5, 20)
        params = changelist.get_filters_params(form_data)
        self.assertIn('datum', params)
        self.assertEqual(params['datum'], expected)
        for key in form_data:
            with self.subTest():
                self.assertNotIn(key, params)
        patcher.stop()

    @mock.patch.object(_admin.BildmaterialAdmin, 'search_form_kwargs', search_form_kwargs)
    def test_preserved_filters_result_list(self):
        # Assert that all items of the result list have the preserved filters
        # attached to the link.
        preserved_filters_name = '_changelist_filters'
        filters = [
            ('single_date', {'datum_0_0': 2020, 'datum_0_1': 5, 'datum_0_2': 20}),
            ('date_range', {
                'datum_0_0': 2020, 'datum_0_1': 5, 'datum_0_2': 20,
                'datum_1_0': 2020, 'datum_1_1': 5, 'datum_1_2': 22
            }),
            ('fk', {'reihe': str(self.reihe.pk)}),
            ('m2m', {'genre': [self.genre1.pk, self.genre2.pk]}),
        ]
        for filter_type, filter_kwargs in filters:
            with self.subTest(filter_type=filter_type):
                response = self.client.get(path=self.changelist_path, data=filter_kwargs)
                expected = urlencode({
                    preserved_filters_name: urlencode(filter_kwargs)
                })
                for result in response.context['results']:
                    if 'href=' not in result:
                        continue
                    with self.subTest():
                        self.assertIn(expected, result)
