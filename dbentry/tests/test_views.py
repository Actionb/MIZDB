from unittest import mock

from django import forms, views
from django.contrib.admin import AdminSite

from dbentry import models as _models
from dbentry.base.views import MIZAdminMixin, OptionalFormView, FixedSessionWizardView
from dbentry.tests.base import MIZTestCase, ViewTestCase
from dbentry.views import MIZ_permission_denied_view, SiteSearchView


class TestMIZAdminMixin(ViewTestCase):

    class view_class(MIZAdminMixin, views.generic.TemplateView):
        title = 'DummyView'
        site_title = 'Testing'
        breadcrumbs_title = 'tests'
        template_name = 'test_template.html'
        admin_site = AdminSite()

    def test_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn('title', context)
        self.assertEqual('DummyView', context['title'])

    def test_site_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn('site_title', context)
        self.assertEqual('Testing', context['site_title'])

    def test_breadcrumbs_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn('breadcrumbs_title', context)
        self.assertEqual('tests', context['breadcrumbs_title'])

    def test_is_popup_in_context_data(self):
        context = self.get_view(self.get_request(data={'_popup': True})).get_context_data()
        self.assertIn('is_popup', context)
        self.assertTrue(context['is_popup'])


class TestOptionalFormView(ViewTestCase):

    view_class = OptionalFormView
    form_class = forms.Form

    def test_get_form(self):
        # OptionalFormView should return a form of the given form_class
        view = self.get_view(request=self.get_request(), form_class=self.form_class)
        self.assertIsInstance(view.get_form(), forms.Form)

    # noinspection SpellCheckingInspection
    def test_get_form_no_formclass(self):
        # If no form_class is set (i.e. the form is optional), get_form() should return None
        view = self.get_view()
        self.assertIsNone(view.get_form())

        # Pass a dummy form_class to get_form(), it should still prioritize being optional
        self.assertIsNone(view.get_form(self.form_class))

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_no_form_class(self, _mocked_invalid, mocked_valid):
        # If view.form_class is None, post should treat the form as optional
        # and call form_valid().
        request = self.post_request()
        view = self.get_view(request)
        self.assertIsNone(view.get_form_class())
        view.post(request)
        self.assertTrue(mocked_valid.called)

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_form_valid(self, _mocked_invalid, mocked_valid):
        # Assert that post calls form_valid if a form_class is set and the form
        # is valid.
        # A form without any fields + any data = bound empty form => form valid.
        request = self.post_request(data={'foo': 'bar'})
        view = self.get_view(request, form_class=self.form_class)
        view.post(request)
        self.assertTrue(mocked_valid.called)

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_form_invalid(self, mocked_invalid, _mocked_valid):
        # Assert that post calls form_invalid if the form is not valid and
        # get_form() is not None.
        form_class = type('Form', (forms.Form, ), {'foo': forms.CharField()})
        # no data for the form:
        request = self.post_request()
        view = self.get_view(request, form_class=form_class)
        view.post(request)
        self.assertTrue(mocked_invalid.called)


class TestPermissionDeniedView(MIZTestCase):

    def test_MIZ_permission_denied_view_missing_template(self):
        response = MIZ_permission_denied_view(None, None, template_name='beepboop')
        from django import http
        self.assertTrue(isinstance(response, http.HttpResponseForbidden))

    def test_MIZ_permission_denied_view(self):
        from django.core.exceptions import PermissionDenied
        exception = PermissionDenied('Exception Text')
        request = self.client.get('').wsgi_request
        response = MIZ_permission_denied_view(request, exception)
        self.assertTrue('exception' in response.context_data)
        self.assertEqual(response.context_data['exception'], 'Exception Text')

        self.assertTrue('is_popup' in response.context_data)


class TestFixedSessionWizardView(ViewTestCase):

    view_class = FixedSessionWizardView

    @mock.patch("dbentry.base.views.SessionWizardView.get_context_data")
    def test_get_context_data(self, mocked_super_get_context_data):
        # Make sure that 'form' is passed to SessionWizardView as a positional
        # argument - unlike other views that accept (only) keyword arguments.
        view = self.get_view(request=self.get_request())
        form = "not actually a form"
        view.get_context_data(form=form)
        self.assertTrue(mocked_super_get_context_data.called)
        call_args = mocked_super_get_context_data.call_args
        self.assertIn(form, call_args[0], msg=call_args)


class TestSiteSearchView(ViewTestCase):

    view_class = SiteSearchView

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = _models.Musiker.objects.create(kuenstler_name='Sharon Silva')
        super().setUpTestData()

    def test_get_result_list(self):
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertIn('Musiker (1)', results[0])

    def test_get_result_list_noperms(self):
        # Assert that get_result_list doesn't return changelist links for users
        # who have no permission to view those changelists.
        view = self.get_view(request=self.get_request(user=self.noperms_user))
        results = view.get_result_list('Silva')
        self.assertFalse(results)

    def test_get_result_list_sorted(self):
        # Assert that the result list is sorted alphabetically by the models'
        # object names.
        _models.Band.objects.create(band_name='Silva')
        view = self.get_view(request=self.get_request())
        results = view.get_result_list('Silva')
        self.assertTrue(results)
        self.assertEqual(len(results), 2)
        self.assertIn('Bands (1)', results[0])
        self.assertIn('Musiker (1)', results[1])

    @mock.patch.object(SiteSearchView, 'render_to_response')
    def test_get(self, mocked_render):
        request_data = {'q': 'Silva'}
        request = self.get_request(data=request_data)
        self.get_view(request).get(request)
        self.assertTrue(mocked_render.called)
        context = mocked_render.call_args[0][0]
        self.assertIn('q', context.keys())
        self.assertEqual(context['q'], 'Silva')
        self.assertIn('results', context.keys())
        results = context['results']
        self.assertTrue(results)
        self.assertEqual(len(results), 1)
        self.assertIn('?q=Silva', results[0])
        self.assertIn('Musiker (1)', results[0])

    @mock.patch.object(SiteSearchView, 'get_result_list')
    @mock.patch.object(SiteSearchView, 'render_to_response')
    def test_get_no_q(self, _mocked_render, mocked_get_result_list):
        # get_result_list should not be called when no search term was provided.
        for data in ({}, {'q': ''}):
            with self.subTest(request_data=data):
                request = self.get_request(data=data)
                self.get_view(request).get(request)
                self.assertFalse(mocked_get_result_list.called)
