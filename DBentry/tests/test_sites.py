from django.contrib.auth.models import Permission
from django.urls import reverse

from DBentry.admin import miz_site
from DBentry.tests.base import RequestTestCase


class TestMIZAdminSite(RequestTestCase):

    def test_index_tools_superuser(self):
        # Check the admintools registered and available to a superuser.
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools')
        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools['bulk_ausgabe'], 'Ausgaben Erstellung')
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
        self.assertFalse(tools)

    def test_app_index_returns_DBentry(self):
        # Assert that app_index returns the tidied up index page of DBentry.
        # The response's app_list should contain additional 'fake' apps
        # like 'Archivgut' etc:
        request = self.get_request(reverse('admin:index'))
        response = miz_site.app_index(request, app_label='DBentry')
        app_list = response.context_data['app_list']
        app_names = [d.get('name') for d in app_list if d.get('name')]
        self.assertIn('Archivgut', app_names)
        self.assertIn('Stammdaten', app_names)
        self.assertIn('Sonstige', app_names)
