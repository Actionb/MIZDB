from .base import DataTestCase

import DBentry.models as _models
from DBentry.factory import make

class TestSignalsAusgabe(DataTestCase):
    
    model = _models.ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.magazin, magazin_name='Testmagazin')
        cls.obj1 = make(cls.model, magazin=cls.mag)
        cls.obj2 = make(cls.model, magazin=cls.mag, ausgabe_jahr__jahr=2000, ausgabe_num__num=12, ausgabe_lnum__lnum=12, ausgabe_monat__monat__monat='Dezember')

        cls.test_data = [cls.obj1, cls.obj2]
        
        super().setUpTestData()
    
    def setUp(self):
        super().setUp()
        # Do pending updates
        self.queryset._update_names()
        
    # post_saved signals
    def test_signal_recieved_from_ausgabe_jahr_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        _models.ausgabe_jahr.objects.create(ausgabe=self.obj1, jahr=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_num_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        _models.ausgabe_num.objects.create(ausgabe=self.obj1, num=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_lnum_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        _models.ausgabe_lnum.objects.create(ausgabe=self.obj1, lnum=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_monat_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        _models.ausgabe_monat.objects.create(ausgabe=self.obj1, monat_id=12)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
        
    # post_delete signals
    def test_signal_recieved_from_ausgabe_jahr_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        _models.ausgabe_jahr.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_num_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        _models.ausgabe_num.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_lnum_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        _models.ausgabe_lnum.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_monat_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        _models.ausgabe_monat.objects.filter(ausgabe=self.obj2, monat_id=12).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
        
    # magazin signals
    def test_signal_recieved_from_magazin(self):
        self.assertAllQSValuesList(self.queryset, '_changed_flag', False)
        self.mag.save() # prompt every ausgabe of mag to update
        self.assertAllQSValuesList(self.queryset, '_changed_flag', True)
