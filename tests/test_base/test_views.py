from unittest import mock

from django import views
from django.contrib.admin import AdminSite
from django.core.exceptions import PermissionDenied

from dbentry.base.views import MIZAdminMixin, SuperUserOnlyMixin
from tests.case import ViewTestCase


class TestMIZAdminMixin(ViewTestCase):
    class view_class(MIZAdminMixin, views.generic.TemplateView):
        title = "DummyView"
        site_title = "Testing"
        breadcrumbs_title = "tests"
        template_name = "test_template.html"
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
        with mock.patch.object(view.admin_site, "each_context") as each_mock:
            view.get_context_data()
        each_mock.assert_called()

    def test_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn("title", context)
        self.assertEqual("DummyView", context["title"])

    def test_site_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn("site_title", context)
        self.assertEqual("Testing", context["site_title"])

    def test_breadcrumbs_title_in_context_data(self):
        context = self.get_view(self.get_request()).get_context_data()
        self.assertIn("breadcrumbs_title", context)
        self.assertEqual("tests", context["breadcrumbs_title"])

    def test_is_popup_in_context_data(self):
        context = self.get_view(self.get_request(data={"_popup": True})).get_context_data()
        self.assertIn("is_popup", context)
        self.assertTrue(context["is_popup"])


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
