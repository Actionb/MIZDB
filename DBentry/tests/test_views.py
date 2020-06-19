from unittest import mock

from django import forms
from django.urls import reverse

from DBentry.base.views import OptionalFormView, FixedSessionWizardView
from DBentry.tests.base import MyTestCase, ViewTestCase
from DBentry.views import MIZ_permission_denied_view, FavoritenView


class TestOptionalFormView(ViewTestCase):

    class DummyView(OptionalFormView):

        def get_template_names(self, *args, **kwargs):
            # So that we do not have to specify a template_name for render_to_response (from form_invalid(form))
            return


    class DummyForm(forms.Form):
        foo = forms.CharField()

    view_class = DummyView
    form_class = DummyForm

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

    def test_post(self):
        # If view.form_class is None, post should treat the form as optional and return form_valid(form) (as per default).
        request = self.post_request()
        view = self.get_view(request, success_url='Test')
        self.assertIsNone(view.get_form_class())
        response = view.post(request)
        self.assertEqual(response.status_code, 302)  # default response is a redirect to the success_url
        self.assertEqual(response.url, 'Test')

        # If view.form_class is not None, and...

        # the form is valid, post should return form_valid(form)
        request = self.post_request(data={'foo': 'bar'})  # will make a form without any fields count as 'bound' and therefor as valid
        view = self.get_view(request, success_url='Test', form_class=self.form_class)
        response = view.post(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, 'Test')

        # the form is invalid, post should return form_invalid(form)
        request = self.post_request()  # no data for the form means it is not bound, and thus not valid
        view = self.get_view(request, success_url='Test', form_class=self.form_class)
        response = view.post(request)
        self.assertEqual(response.status_code, 200)  # no redirect to the success_url


class TestFavoritenView(ViewTestCase):

    view_class = FavoritenView
    path = reverse("favoriten")

    def test_get_success_url(self):
        request = self.get_request()
        view = self.get_view(request)
        self.assertEqual(view.get_success_url(), '')

    def test_get_object(self):
        # Test that get_object creates a new entry in the Favoriten table if necessary
        request = self.get_request()
        view = self.get_view(request)
        view.model.objects.filter(user=request.user).delete()  # delete any remnants

        new_entry = view.get_object()  # user has no Favoriten yet, create an entry in Favoriten
        self.assertEqual(new_entry.user, self.super_user)
        self.assertTrue(view.model.objects.filter(user=request.user).exists())

        self.assertEqual(view.get_object(), new_entry)  # direct access to Favoriten via queryset


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
