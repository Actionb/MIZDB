"""
This is meant to test an action at its 'backend', i.e. testing the availablity of the action through a changelist.
Probably not going to stay.
"""

from .base import *

from DBentry.admin import *

class TestAdminActionsArtikel(AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    test_data_count = 3
        
    def test_merge_records_low_count(self):
        # qs.count() == 1
        response = self.call_action('merge_records', self.qs_obj1)
        self.assertEqual(response.status_code, 302)
        expected_message = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.'
        self.assertMessageSent(response.wsgi_request, expected_message)
        
    def test_merge_records_not_allowed(self):
        # qs.count() > 1 with different ausgaben => merge not allowed
        DataFactory().create_obj(artikel, create_new = True)
        response = self.call_action('merge_records', self.queryset)
        self.assertEqual(response.status_code, 302)
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(response.wsgi_request, expected_message)
    
    def test_merge_records_success(self):
        # qs.count() >1 with same ausgabe
        response = self.call_action('merge_records', self.queryset)
        self.assertEqual(response.status_code, 200)

class TestAdminActionAusgabe(AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    test_data_count = 3
    
    def test_bulk_jg(self):
        response = self.call_action('bulk_jg', self.queryset)
        self.assertEqual(response.status_code, 200)
        
    def test_add_bestand(self):
        from DBentry.constants import ZRAUM_ID,  DUPLETTEN_ID
        lagerort.objects.create(pk=ZRAUM_ID, ort='Bestand')
        lagerort.objects.create(pk=DUPLETTEN_ID, ort='Dublette')
        response = self.call_action('add_bestand', self.queryset)
        self.assertEqual(response.status_code, 200)
    
    
