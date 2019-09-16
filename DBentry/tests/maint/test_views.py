from unittest.mock import patch, Mock

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.urls import reverse, resolve
from django.utils.http import unquote

from DBentry import models as _models
from DBentry import utils
from DBentry.actions.views import MergeViewWizarded
from DBentry.maint.views import DuplicateObjectsView, ModelSelectView
from DBentry.tests.base import ViewTestCase
from DBentry.tests.mixins import TestDataMixin


class TestModelSelectView(ViewTestCase):

    view_class = ModelSelectView

    def test_get_context_data(self):
        initkwargs = {
            'submit_value': 'testing_value',
            'submit_name': 'testing_name',
            'form_method': 'testing_form_method'
        }
        view = self.get_view(self.get_request(), **initkwargs)
        context = view.get_context_data()
        for context_variable, expected in initkwargs.items():
            with self.subTest(var=context_variable):
                self.assertIn(context_variable, context)
                self.assertEqual(context[context_variable], expected)

    def test_get(self):
        # Assert that get() redirects to the success url if
        # the view's submit_name is in the GET querydict.
        request = self.get_request(data={'testing': 'yes'})
        view = self.get_view(request, submit_name='testing')
        with patch.object(view, 'get_success_url', return_value='admin:index'):
            response = view.get(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/admin/')

    def test_get_success_url(self):
        # Assert that get_success_url returns a resolveable url.
        view = self.get_view(self.get_request(), next_view='admin:index')
        with patch.object(view, 'get_next_view_kwargs', return_value={}):
            self.assertEqual(view.get_success_url(), '/admin/')

    def test_get_next_view_kwargs(self):
        view = self.get_view(self.get_request(data={'model_select': 'some_model'}))
        self.assertEqual(view.get_next_view_kwargs(), {'model_name': 'some_model'})


class TestDuplicateObjectsView(TestDataMixin, ViewTestCase):

    model = _models.band
    view_class = DuplicateObjectsView

    @classmethod
    def setUpTestData(cls):
        # Not using make() as the factory for band has 'band_name' in
        # get_or_create; calling make(band_name = 'X') repeatedly will always
        # return the same band object.
        cls.test_data = [
            _models.band.objects.create(id=i, band_name='Beep')
            for i in range(1, 4)
        ]
        super().setUpTestData()

    def test_availabilty(self):
        url = reverse('dupes', kwargs={'model_name': 'band'})
        self.assertTrue(resolve(url))

        # Assert that no queries are being done accessing the page; an oversight
        # led to the page querying for duplicates without any fields when request.
        # one query each for: session, user (must be a client thing)
        with self.assertNumQueries(2):
            self.client.get(url)

    def test_setup_exceptions(self):
        # Assert that setup() raises exceptions when:
        # - the kwarg 'model_name' is not provided OR
        # - when no model matching that name exists.
        view = self.view_class()
        request = self.get_request()
        with self.assertRaises(TypeError):
            view.setup(request)
        with self.assertRaises(ValueError):
            view.setup(request, model_name='WOOP')

    def test_post_redirects_to_self_after_merging(self):
        # Assert that post redirects back to itself after a merge.
        path = reverse('dupes', kwargs = {'model_name': 'band'})
        request = self.post_request(path, data = {ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        # patch the as_view method of MergeViewWizarded to return None,
        # thereby emulating a successful merge without conflicts.
        def mocked_as_view(*args, **kwargs):
            return Mock(return_value = None)
        with patch.object(MergeViewWizarded, 'as_view', new = mocked_as_view):
            response = view.post(request)
            self.assertEqual(response.url, path)

    def test_post_calls_merge_view(self):
       # Assert that a post request will call the merge view.
        model_admin = utils.get_model_admin_for_model(self.model)
        request = self.post_request(data = {ACTION_CHECKBOX_NAME: ['1', '2']})
        view = self.get_view(request, kwargs={'model_name': 'band'})

        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 1)
        kwargs = mocked_as_view.call_args[1]
        self.assertIn('model_admin', kwargs)
        self.assertEqual(kwargs['model_admin'].__class__, model_admin.__class__)
        self.assertIn('queryset', kwargs)
        self.assertEqual(
            list(kwargs['queryset'].values_list('pk', flat=True)),
            [self.obj1.pk, self.obj2.pk]
        )

    def test_post_does_not_call_merge_view_with_no_selects(self):
        # Assert that a post request will NOT call the merge view when no items
        # in a sub list are selected for a merge.
        request = self.post_request(data = {ACTION_CHECKBOX_NAME: []})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        with patch.object(MergeViewWizarded, 'as_view') as mocked_as_view:
            view.post(request)
        self.assertEqual(mocked_as_view.call_count, 0)

    def test_build_duplicates_items(self):
        # Assert that build_duplicates_items returns the correct items.
        changeform_url = unquote(
            reverse('admin:DBentry_band_change', args=['{pk}'])
        )
        link_template = '<a href="{url}">{name}</a>'

        request = self.get_request(data={'base': ['band_name']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        # A validated and cleaned form is required.
        self.assertTrue(form.is_valid())

        items = view.build_duplicates_items(form)
        self.assertEqual(
            len(items), 1,
            msg = "There should be only one set of duplicate objects."
        )
        self.assertEqual(
            len(items[0]), 2,
            msg = "Should contain one set of duplicate objects and the url to "
            "their changelist."
        )
        self.assertEqual(
            len(items[0][0]), 3,
            msg = "Should contain the three duplicate objects."
        )
        for dupe_item in items[0][0]:
            with self.subTest():
                self.assertEqual(len(dupe_item), 3)
                self.assertIsInstance(
                    dupe_item[0], self.model,
                    msg="Duplicate object should be an instance of "
                    "{!s}.".format(self.model)
                )
                expected_link = link_template.format(
                    url=changeform_url.format(pk=dupe_item[0].pk),
                    name=str(dupe_item[0])
                )
                self.assertEqual(
                    dupe_item[1], expected_link,
                    msg="Should be link to change form of object."
                )
                self.assertEqual(
                    dupe_item[2], ['Beep'],
                    msg="Should be the duplicate object's values of the "
                    "fields the duplicates were found with."
                )
        self.assertIsInstance(
            items[0][1], str,
            msg="Should be the url to the changelist of the duplicate objects."
        )
        self.assertIn(
            '?', items[0][1],
            msg="Changelist url should be of format <changelist>?id__in=[ids]"
        )
        cl_url, _query_params = items[0][1].split('?')
        self.assertEqual(cl_url, reverse('admin:DBentry_band_changelist'))

    def test_build_duplicates_headers(self):
        # Assert that the correct (field.verbose_name capitalized) headers are
        # returned. Headers are built from the labels of the established choices.
        test_data = [
            ({'base': ['band_name']}, 'Bandname'),
            ({'m2m': ['genre']}, 'Genre'),
            ({'reverse': ['band_alias__alias']}, 'Alias')
        ]
        for request_data, expected in test_data:
            with self.subTest(data=request_data):
                request = self.get_request(data=request_data)
                view = self.get_view(request, kwargs={'model_name': 'band'})
                form = view.get_form()
                self.assertTrue(form.is_valid())
                headers = view.build_duplicates_headers(form)
                self.assertIn(expected, headers)

    def test_build_duplicates_headers_grouped_choices(self):
        request = self.get_request(data={'reverse': ['band_alias__alias']})
        view = self.get_view(request, kwargs={'model_name': 'band'})
        form = view.get_form()
        form.fields['reverse'].choices = [
            ('Alias', [('band_alias__alias', 'Alias')])
        ]
        self.assertTrue(form.is_valid())
        headers = view.build_duplicates_headers(form)
        self.assertIn('Alias', headers)
