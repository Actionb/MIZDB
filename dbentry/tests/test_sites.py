from unittest import skip
from unittest.mock import DEFAULT, patch, Mock

from django.contrib.auth.models import Permission, User
from django.core import checks
from django.urls import reverse

from dbentry import models as _models
from dbentry.sites import MIZAdminSite, miz_site, register_tool
from dbentry.tests.base import RequestTestCase


class TestMIZAdminSite(RequestTestCase):

    def test_index_tools_superuser(self):
        # Check the admintools registered and available to a superuser.
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools')
        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools['bulk_ausgabe'], 'Ausgaben Erstellung')
        self.assertIn('site_search', tools)
        self.assertEqual(tools['site_search'], 'Datenbank durchsuchen')
        self.assertIn('dupes_select', tools)
        self.assertEqual(tools['dupes_select'], 'Duplikate finden')
        self.assertNotIn('import_select', tools)

    def test_index_tools_mitarbeiter(self):
        # Check that staff users only have access to a selected number
        # of index tools. Here: only bulk_ausgabe and not dupes_select.
        perms = Permission.objects.filter(codename='add_ausgabe')
        self.staff_user.user_permissions.set(perms)
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools').copy()

        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools.pop('bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('site_search', tools)
        self.assertEqual(tools.pop('site_search'), 'Datenbank durchsuchen')
        self.assertFalse(tools)

    @skip("Permission checks disabled again: commit 0190e654")
    def test_index_tools_view_only(self):
        # Assert that view-only user (i.e. visitors) only see the site_search
        # tool.
        visitor_user = User.objects.create_user(
            username='visitor', password='besucher', is_staff=True)
        visitor_user.user_permissions.set([
            Permission.objects.get(codename='view_ausgabe'),
        ])
        self.client.force_login(visitor_user)
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools').copy()
        self.assertIn('site_search', tools)
        self.assertEqual(tools.pop('site_search'), 'Datenbank durchsuchen')
        self.assertFalse(tools)

    @patch('dbentry.sites.admin.AdminSite.app_index')
    def test_app_index_returns_dbentry(self, mocked_super_app_index):
        # Assert that a request for the app_index of 'dbentry' uses the index()
        # method instead.
        # (can't really test a full on request-response process because mocking
        #   index or super.app_index breaks it)
        site = MIZAdminSite()
        for app_label, index_called in [('dbentry', True), ('Beep', False)]:
            with self.subTest(app_label=app_label):
                with patch.object(site, 'index') as mocked_index:
                    site.app_index(request=None, app_label=app_label)
                    if index_called:
                        self.assertTrue(mocked_index.called)
                        self.assertFalse(mocked_super_app_index.called)
                    else:
                        self.assertFalse(mocked_index.called)
                        self.assertTrue(mocked_super_app_index.called)

    def test_app_index_categories(self):
        # Assert that the dbentry app_list contains the additional 'fake' apps
        # that organize the various models of the app.
        request = self.get_request(path=reverse('admin:index'))
        response = miz_site.app_index(request, app_label='dbentry')
        app_list = response.context_data['app_list']
        app_names = [d.get('name') for d in app_list if d.get('name')]
        for category in ['Archivgut', 'Stammdaten', 'Sonstige']:
            with self.subTest():
                self.assertIn(category, app_names)

    @patch("dbentry.sites.admin.AdminSite.check")
    def test_check(self, mocked_super_check):
        # Assert that the check finds tools with invalid url names.
        mocked_super_check.return_value = []
        with patch.object(miz_site, 'tools', new=[]):
            self.assertFalse(miz_site.check(None))
            miz_site.tools.append((None, '404_url', '', False))
            errors = miz_site.check(None)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)

    def test_app_index(self):
        # Check that /admin/dbentry/ and /admin/ resolve to the expected index
        # views.
        response = self.client.get('/admin/dbentry/')
        self.assertEqual(
            response.resolver_match.func.__name__, MIZAdminSite.app_index.__name__)

        response = self.client.get('/admin/')
        self.assertEqual(
            response.resolver_match.func.__name__, MIZAdminSite.index.__name__)

    def test_changelist_availability_superuser(self):
        # Assert that the changelists of all registered ModelAdmins can be
        # reached.
        self.client.force_login(self.super_user)
        for model in miz_site._registry:
            opts = model._meta
            with self.subTest(model_name=opts.model_name):
                path = reverse(
                    "%s:%s_%s_changelist" %
                    (miz_site.name, opts.app_label, opts.model_name)
                )
                with self.assertNotRaises(Exception):
                    response = self.client.get(path=path)
                self.assertEqual(response.status_code, 200, msg=path)

    def test_build_admintools_context_superuser_only(self):
        # Assert that build_admintools_context only includes tools that are
        # flagged with superuser_only=True for superusers.
        site = MIZAdminSite()
        # Items in the tools list are a 4-tuple:
        #   (tool, url_name, index_label, superuser_only)
        site.tools = [(None, '', '', True)]
        request = self.get_request(user=self.noperms_user)
        self.assertFalse(site.build_admintools_context(request))
        request = self.get_request(user=self.super_user)
        # Mock your way around the permission/availability checks following the
        # superuser checks.
        with patch.multiple('dbentry.sites', reverse=DEFAULT):
            self.assertTrue(site.build_admintools_context(request))

    def test_add_categories_no_category(self):
        # Assert that add_categories puts ModelAdmins with a category that isn't
        # one of the three default ones (Archivgut, Stammdaten, Sonstige) into
        # the 'Sonstige' category.
        # (lazily just use miz_site instead of mocking everything)
        model_admin = miz_site._registry[_models.Artikel]
        for index_category in ('Sonstige', 'Beep', None):
            app_list = [{'app_label': 'dbentry', 'models': [{'object_name': 'Artikel'}]}]
            with self.subTest(index_category=str(index_category)):
                with patch.object(model_admin, 'index_category', new=index_category):
                    app_list = miz_site.add_categories(app_list)
                    self.assertEqual(len(app_list), 3, app_list)
                    self.assertEqual(app_list[-1]['name'], 'Sonstige')
                    sonstige_category = app_list[-1]
                    self.assertEqual(len(sonstige_category['models']), 1)
                    self.assertEqual(sonstige_category['models'][0]['object_name'], 'Artikel')

    def test_add_categories_no_dbentry_app(self):
        # Assert that add_categories returns an empty list if no 'dbentry' app
        # can be found in the given app_list.
        site = MIZAdminSite()
        app_list = []
        self.assertFalse(site.add_categories(app_list))
        app_list.append({'app_label': 'Beep', 'models': []})
        self.assertFalse(site.add_categories(app_list))
        app_list.append({'app_label': 'dbentry', 'models': []})
        self.assertTrue(site.add_categories(app_list))

    def test_register_tool(self):
        # Assert that the register_tool decorator calls a site's register_tool
        # method with the right arguments and adds the view to the list of tool
        # views.
        site = Mock()
        dummy_view = object()
        register_tool(
            url_name='url_name',
            index_label='index_label',
            superuser_only='True',
            site=site
        )(dummy_view)
        site.register_tool.assert_called_with(
            dummy_view, 'url_name', 'index_label', 'True'
        )

        site = MIZAdminSite()
        register_tool(
            url_name='url_name',
            index_label='index_label',
            superuser_only='True',
            site=site
        )(dummy_view)
        self.assertIn((dummy_view, 'url_name', 'index_label', 'True'), site.tools)
