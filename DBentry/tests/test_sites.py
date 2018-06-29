from .base import *

from DBentry.sites import MIZAdminSite

class TestMIZAdminSite(RequestTestCase):
    
    def test_index_tools(self):
        #TODO: add Wartung
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools')
        self.assertIn('bulk_ausgabe', tools)
        self.assertEqual(tools.get('bulk_ausgabe'), 'Ausgaben Erstellung')
        self.assertIn('favoriten', tools)
        self.assertEqual(tools.get('favoriten'), 'Favoriten Verwaltung')
        self.assertIn('import_select', tools)
        self.assertEqual(tools.get('import_select'), 'Discogs Import')
        
    def test_index_tools_noperms(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('admin:index'))
        tools = response.context_data.get('admintools')
        self.assertEqual(len(tools), 0, msg=str(tools))
