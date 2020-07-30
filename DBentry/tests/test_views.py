from unittest import mock

from django import forms

from DBentry.base.views import OptionalFormView, FixedSessionWizardView
from DBentry.tests.base import MyTestCase, ViewTestCase
from DBentry.views import MIZ_permission_denied_view


class TestOptionalFormView(ViewTestCase):

    view_class = OptionalFormView
    form_class = forms.Form

    def test_get_form(self):
        # OptionalFormView should return a form of the given form_class
        view = self.get_view(request=self.get_request(), form_class=self.form_class)
        self.assertIsInstance(view.get_form(), forms.Form)

    def test_get_form_no_formclass(self):
        # If no form_class is set (i.e. the form is optional), get_form() should return None
        view = self.get_view()
        self.assertIsNone(view.get_form())

        # Pass a dummy form_class to get_form(), it should still prioritize being optional
        self.assertIsNone(view.get_form(self.form_class))

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_no_form_class(self, mocked_invalid, mocked_valid):
        # If view.form_class is None, post should treat the form as optional
        # and call form_valid().
        request = self.post_request()
        view = self.get_view(request)
        self.assertIsNone(view.get_form_class())
        view.post(request)
        self.assertTrue(mocked_valid.called)

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_form_valid(self, mocked_invalid, mocked_valid):
        # Assert that post calls form_valid if a form_class is set and the form
        # is valid.
        # A form without any fields + any data = bound empty form => form valid.
        request = self.post_request(data={'foo': 'bar'})
        view = self.get_view(request, form_class=self.form_class)
        view.post(request)
        self.assertTrue(mocked_valid.called)

    @mock.patch.object(OptionalFormView, 'form_valid')
    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_form_invalid(self, mocked_invalid, mocked_valid):
        # Assert that post calls form_invalid if the form is not valid and
        # get_form() is not None.
        form_class = type('Form', (forms.Form, ), {'foo': forms.CharField()})
        # no data for the form:
        request = self.post_request()
        view = self.get_view(request, form_class=form_class)
        view.post(request)
        self.assertTrue(mocked_invalid.called)


class TestPermissionDeniedView(MyTestCase):

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

    @mock.patch("DBentry.base.views.SessionWizardView.get_context_data")
    def test_get_context_data(self, mocked_super_get_context_data):
        # Make sure that 'form' is passed to SessionWizardView as a positional
        # argument - unlike other views that accept (only) keyword arguments.
        view = self.get_view(request=self.get_request())
        form = "not actually a form"
        view.get_context_data(form=form)
        self.assertTrue(mocked_super_get_context_data.called)
        call_args = mocked_super_get_context_data.call_args
        self.assertIn(form, call_args[0], msg=call_args)
