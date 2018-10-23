from .base import *

from DBentry.admin import miz_site

class TestMIZAdminSite(RequestTestCase):
    
    def test_index_tools_superuser(self):
        #FIXME: import_select is in tools when the full test suite is run 
        # -- and it is NOT in tools when only TestMIZAdminSite is run
        # It's also not in the admintools of the production site.
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools')
        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools.get('bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('favoriten', tools)
        self.assertEqual(tools.get('favoriten'), 'Favoriten Verwaltung')
        self.assertIn('dupes_select', tools)
        self.assertEqual(tools.get('dupes_select'), 'Duplikate finden')
#        self.assertIn('maint_main', tools)
#        self.assertEqual(tools.get('maint_main'), 'Wartung')
#        self.assertNotIn('import_select', tools)

    def test_index_tools_mitarbeiter(self):
        from django.contrib.auth.models import Permission
        perms = Permission.objects.filter(codename__in=('add_ausgabe', 'add_favoriten', 'change_favoriten', 'delete_favoriten'))
        self.staff_user.user_permissions.set(perms)
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools').copy()
        
        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools.pop('bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('favoriten', tools)
        self.assertEqual(tools.pop('favoriten'), 'Favoriten Verwaltung')
        self.assertEqual(tools.pop('help_index'), 'Hilfe')
        self.assertFalse(tools)
    
#    @tag("wip")
#    def test_index_tools_noperms(self):
#        # Should 
#        self.client.force_login(self.noperms_user)
#        response = self.client.get(reverse('admin:index'))
#        print()
#        print(response.status_code)
#        print(response.resolver_match.func)
#        print(response.templates)
#        print(response.content)
#        tools = response.context_data.get('admintools')
#        self.assertFalse(tools)
        
    def test_app_index_returns_DBentry(self):
        # Assert that app_index returns the tiedied up index page of DBentry
        # the response's app_list should contain additional 'fake' apps like 'Archivgut' etc.
        request = self.get_request(reverse('admin:index'))
        app_list = miz_site.app_index(request, app_label = 'DBentry').context_data['app_list']
        
        app_names = [d.get('name') for d in app_list if d.get('name')]
        self.assertIn('Archivgut', app_names)
        self.assertIn('Stammdaten', app_names)
        self.assertIn('Sonstige', app_names)
        
