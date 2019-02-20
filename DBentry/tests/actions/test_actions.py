"""
This is meant to test an action at its 'backend', i.e. testing the availablity of the action through a changelist.
Probably not going to stay.
"""

from ..base import AdminTestCase

from django.utils.translation import override as translation_override

from DBentry.admin import ArtikelAdmin, AusgabenAdmin
from DBentry.models import artikel, ausgabe, lagerort
from DBentry.factory import make

class TestAdminActionsArtikel(AdminTestCase):
    
    model_admin_class = ArtikelAdmin
    model = artikel
    
    @classmethod
    def setUpTestData(cls):
        ausg = make(ausgabe)
        cls.obj1 = make(cls.model, ausgabe = ausg)
        cls.obj2 = make(cls.model, ausgabe = ausg)
        cls.obj3 = make(cls.model)
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        
        super().setUpTestData()
    
    @translation_override(language = None)
    def test_merge_records_low_count(self):
        # qs.count() == 1
        response = self.call_action('merge_records', self.qs_obj1)
        self.assertEqual(response.status_code, 302)
        expected_message = 'Es müssen mindestens zwei Objekte aus der Liste ausgewählt werden, um diese Aktion durchzuführen.'
        self.assertMessageSent(response.wsgi_request, expected_message)
        
    @translation_override(language = None)
    def test_merge_records_not_allowed(self):
        # qs.count() > 1 with different ausgaben => merge not allowed
        response = self.call_action('merge_records', self.queryset.filter(pk__in=[self.obj1.pk, self.obj3.pk]))
        self.assertEqual(response.status_code, 302)
        expected_message = 'Die ausgewählten Artikel gehören zu unterschiedlichen Ausgaben.'
        self.assertMessageSent(response.wsgi_request, expected_message)
    
    def test_merge_records_success(self):
        # qs.count() >1 with same ausgabe
        response = self.call_action('merge_records', self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk]))
        self.assertEqual(response.status_code, 200)

class TestAdminActionAusgabe(AdminTestCase):
    
    model_admin_class = AusgabenAdmin
    model = ausgabe
    raw_data = [{'magazin__magazin_name':'Testmagazin'}, {'magazin__magazin_name':'Testmagazin'}, {'magazin__magazin_name':'Testmagazin'}]
    
    def test_bulk_jg(self):
        response = self.call_action('bulk_jg', self.queryset)
        self.assertEqual(response.status_code, 200)
        
    def test_add_bestand(self):
        from DBentry.constants import ZRAUM_ID,  DUPLETTEN_ID
        lagerort.objects.create(pk=ZRAUM_ID, ort='Bestand')
        lagerort.objects.create(pk=DUPLETTEN_ID, ort='Dublette')
        response = self.call_action('add_bestand', self.queryset)
        self.assertEqual(response.status_code, 200)
    
    
