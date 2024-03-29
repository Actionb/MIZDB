from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.urls import reverse

from dbentry import models as _models
from dbentry.base.admin import MIZModelAdmin
from dbentry.sites import MIZAdminSite, miz_site
from tests.case import RequestTestCase

miz_admin_site = MIZAdminSite()


@admin.register(_models.Artikel, site=miz_admin_site)
class ArtikelAdmin(MIZModelAdmin):
    index_category = 'Archivgut'


class TestMIZAdminSite(RequestTestCase):
    """Test the base admin site class MIZAdminSite."""
    site = miz_admin_site

    def test_each_context(self):
        """Assert that the Wiki URL is added to the context."""
        with override_settings(WIKI_URL='localhost/wiki/index.html'):
            context = self.site.each_context(self.get_request())
            self.assertIn('wiki_url', context)
            self.assertEqual('localhost/wiki/index.html', context['wiki_url'])
        with override_settings(WIKI_URL=None):
            context = self.site.each_context(self.get_request())
            self.assertNotIn('wiki_url', context)

    @patch('dbentry.tools.sites.IndexToolsSite.app_index')
    def test_app_index_returns_dbentry(self, super_mock):
        """
        Assert that a request for the app index of app 'dbentry' returns the
        main admin index (which would include the fake apps).
        """
        for app_label, index_called in [('dbentry', True), ('Beep', False)]:
            with self.subTest(app_label=app_label):
                with patch.object(self.site, 'index') as index_mock:
                    self.site.app_index(request=None, app_label=app_label)
                    if index_called:
                        self.assertTrue(index_mock.called)
                        self.assertFalse(super_mock.called)
                    else:
                        self.assertFalse(index_mock.called)
                        self.assertTrue(super_mock.called)

    def test_app_index_categories(self):
        """
        Assert that the dbentry app_list contains the additional 'fake' apps
        that organize the various models of the app.
        """
        request = self.get_request(path=reverse('admin:index'))
        response = self.site.app_index(request, app_label='dbentry')
        app_list = response.context_data['app_list']  # noqa
        app_names = [d.get('name') for d in app_list if d.get('name')]
        for category in ['Archivgut', 'Stammdaten', 'Sonstige']:
            with self.subTest():
                self.assertIn(category, app_names)

    def test_add_categories_no_category(self):
        """
        Assert that add_categories puts ModelAdmins with a category that isn't
        one of the three default ones (Archivgut, Stammdaten, Sonstige) into
        the 'Sonstige' category.
        """
        for index_category in ('Sonstige', 'Beep', None):
            app_list = [{'app_label': 'dbentry', 'models': [{'object_name': 'Artikel'}]}]
            with self.subTest(index_category=str(index_category)):
                ArtikelAdmin.index_category = index_category
                app_list = self.site.add_categories(app_list)
                self.assertEqual(len(app_list), 3, app_list)
                self.assertEqual(app_list[-1]['name'], 'Sonstige')
                sonstige_category = app_list[-1]
                self.assertEqual(len(sonstige_category['models']), 1)
                self.assertEqual(sonstige_category['models'][0]['object_name'], 'Artikel')

    def test_add_categories_no_dbentry_app(self):
        """
        Assert that add_categories returns an empty list if no 'dbentry' app
        can be found in the given app_list.
        """
        app_list = []
        self.assertFalse(self.site.add_categories(app_list))
        app_list.append({'app_label': 'Beep', 'models': []})
        self.assertFalse(self.site.add_categories(app_list))
        app_list.append({'app_label': 'dbentry', 'models': []})
        self.assertTrue(self.site.add_categories(app_list))


class TestMIZSite(RequestTestCase):
    """Test the admin site 'miz_site'."""

    def test_index_tools_superuser(self):
        """Check the admintools registered and available to a superuser."""
        response = self.get_response(reverse(f'{miz_site.name}:index'), user=self.super_user)
        self.assertTrue('admintools' in response.context_data)
        tools = response.context_data.get('admintools')

        self.assertIn('tools:bulk_ausgabe', tools)
        self.assertEqual(tools['tools:bulk_ausgabe'], 'Ausgaben Erstellung')
        self.assertIn('tools:site_search', tools)
        self.assertEqual(tools['tools:site_search'], 'Datenbank durchsuchen')
        self.assertIn('tools:dupes_select', tools)
        self.assertEqual(tools['tools:dupes_select'], 'Duplikate finden')

    def test_index_tools_mitarbeiter(self):
        """
        Check that staff users only have access to a selected number of index
        tools.
        """
        ct = ContentType.objects.get_for_model(_models.Ausgabe)
        perms = Permission.objects.filter(codename='add_ausgabe', content_type=ct)
        self.staff_user.user_permissions.set(perms)

        response = self.get_response(reverse(f'{miz_site.name}:index'), user=self.staff_user)
        self.assertTrue('admintools' in response.context_data)
        tools = response.context_data.get('admintools').copy()

        self.assertIn('tools:bulk_ausgabe', tools)
        self.assertEqual(tools.pop('tools:bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('tools:site_search', tools)
        self.assertEqual(tools.pop('tools:site_search'), 'Datenbank durchsuchen')
        self.assertFalse(tools)

    def test_index_tools_view_only(self):
        """
        Assert that view-only users (i.e. visitors) only see the site_search
        tool.
        """
        visitor_user = User.objects.create_user(
            username='visitor', password='besucher', is_staff=True
        )
        ct = ContentType.objects.get_for_model(_models.Ausgabe)
        visitor_user.user_permissions.set(
            [Permission.objects.get(codename='view_ausgabe', content_type=ct)]
        )

        response = self.get_response(reverse(f'{miz_site.name}:index'), user=visitor_user)
        self.assertTrue('admintools' in response.context_data)
        tools = response.context_data.get('admintools').copy()

        self.assertIn('tools:site_search', tools)
        self.assertEqual(tools.pop('tools:site_search'), 'Datenbank durchsuchen')
        self.assertFalse(tools)

    def test_changelist_availability_superuser(self):
        """
        Assert that the changelists of all registered ModelAdmins can be
        reached.
        """
        self.client.force_login(self.super_user)
        for model in miz_site._registry:
            opts = model._meta
            with self.subTest(model_name=opts.model_name):
                path = reverse(f"{miz_site.name}:{opts.app_label}_{opts.model_name}_changelist")
                with self.assertNotRaises(Exception):
                    response = self.client.get(path=path)
                self.assertEqual(response.status_code, 200, msg=path)

    def test_app_index(self):
        """
        Assert that the paths '/admin/dbentry/' and '/admin/' resolve to the
        expected index view functions.
        """
        response = self.client.get('/admin/dbentry/')
        self.assertEqual(
            response.resolver_match.func.__name__, MIZAdminSite.app_index.__name__
        )

        response = self.client.get('/admin/')
        self.assertEqual(
            response.resolver_match.func.__name__, MIZAdminSite.index.__name__
        )
