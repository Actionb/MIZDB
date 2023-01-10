from unittest import mock

from django import forms, views
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied

from dbentry.base.views import (
    FixedSessionWizardView, MIZAdminMixin, OptionalFormView, SuperUserOnlyMixin
)
from tests.case import ViewTestCase


class TestMIZAdminMixin(ViewTestCase):
    class view_class(MIZAdminMixin, views.generic.TemplateView):
        title = 'DummyView'
        site_title = 'Testing'
        breadcrumbs_title = 'tests'
        template_name = 'test_template.html'
        admin_site = AdminSite()

    def test_init_sets_admin_site(self):
        """
        Assert that init sets the admin_site attribute when provided with an
        admin_site argument.
        """
        self.assertEqual(self.view_class(admin_site=1).admin_site, 1)
        self.assertEqual(self.view_class().admin_site, self.view_class.admin_site)

    def test_get_context_data_calls_each_context(self):
        """get_context_data should call the each_context method of the admin site."""
        view = self.get_view(self.get_request())
        with mock.patch.object(view.admin_site, 'each_context') as each_mock:
            view.get_context_data()
        each_mock.assert_called()

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
    class TestForm(forms.Form):
        spam = forms.CharField()

    class view_class(OptionalFormView):
        form_class = forms.Form

    def test_get_form(self):
        """get_form should return a form of the view's form_class."""
        view = self.get_view(self.get_request())
        self.assertIsInstance(view.get_form(), forms.Form)

    def test_get_form_no_form_class(self):
        """get_form should return None, if the no form_class is set."""
        view = self.get_view(self.get_request(), form_class=None)
        self.assertIsNone(view.get_form())

    @mock.patch.object(OptionalFormView, 'form_valid')
    def test_post_no_form_class(self, form_valid_mock):
        """
        If view.form_class is None, post should treat the form as optional and
        call form_valid.
        """
        request = self.post_request()
        view = self.get_view(request, form_class=None)
        self.assertIsNone(view.get_form_class())
        view.post(request)
        self.assertTrue(form_valid_mock.called)

    @mock.patch.object(OptionalFormView, 'form_valid')
    def test_post_form_valid(self, form_valid_mock):
        """
        Assert that post calls form_valid, if a form_class is set and the form
        is valid.
        """
        # A form without any fields + any data = bound empty form => form valid.
        request = self.post_request(data={'foo': 'bar'})
        view = self.get_view(request)
        view.post(request)
        self.assertTrue(form_valid_mock.called)

    @mock.patch.object(OptionalFormView, 'form_invalid')
    def test_post_form_invalid(self, form_invalid_mock):
        """
        Assert that post calls form_invalid, if a form_class is set and the
        form is not valid.
        """
        request = self.post_request()  # no data for the form
        view = self.get_view(request, form_class=self.TestForm)
        view.post(request)
        self.assertTrue(form_invalid_mock.called)


class TestFixedSessionWizardView(ViewTestCase):
    class TestForm(forms.Form):
        spam = forms.CharField()

    view_class = FixedSessionWizardView

    def test_get_context_data(self):
        """Assert that get_context_data can deal with a 'form' kwarg."""
        # See: https://github.com/jazzband/django-formtools/commit/bd970f673de8916fc058a2beef835139cbfe4ed6
        view = self.get_view(self.get_request())
        patches = {
            'storage': mock.Mock(extra_data={}), 'steps': mock.DEFAULT,
            'prefix': mock.DEFAULT
        }

        with mock.patch.multiple(view, **patches, create=True):
            with mock.patch('formtools.wizard.views.ManagementForm'):
                context = view.get_context_data(spam='egg', form=self.TestForm())
        self.assertIn('form', context)


class SuperUserOnlyTest(ViewTestCase):
    class view_class(SuperUserOnlyMixin, views.View):
        pass

    def test_super_user(self):
        request = self.post_request(user=self.super_user)
        view = self.get_view(request)
        with self.assertNotRaises(PermissionDenied):
            view.dispatch(request)

    def test_noperms_user(self):
        request = self.post_request(user=self.noperms_user)
        view = self.get_view(request)
        with self.assertRaises(PermissionDenied):
            view.dispatch(request)
