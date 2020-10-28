from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core import checks
from django.urls import reverse

from DBentry.sites import MIZAdminSite, miz_site
from DBentry.tests.base import RequestTestCase


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
        perms = Permission.objects.filter(codename__in=('add_ausgabe'))
        self.staff_user.user_permissions.set(perms)
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools').copy()

        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools.pop('bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('site_search', tools)
        self.assertEqual(tools.pop('site_search'), 'Datenbank durchsuchen')
        self.assertFalse(tools)

    def test_app_index_returns_DBentry(self):
        # Assert that app_index returns the tidied up index page of DBentry.
        # The response's app_list should contain additional 'fake' apps
        # like 'Archivgut' etc:
        request = self.get_request(path=reverse('admin:index'))
        response = miz_site.app_index(request, app_label='DBentry')
        app_list = response.context_data['app_list']
        app_names = [d.get('name') for d in app_list if d.get('name')]
        for category in ['Archivgut', 'Stammdaten', 'Sonstige']:
            with self.subTest():
                self.assertIn(category, app_names)

    @patch("DBentry.sites.admin.AdminSite.check")
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
        # Check that /admin/DBentry/ and /admin/ resolve to the expected index
        # views.
        response = self.client.get('/admin/DBentry/')
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
