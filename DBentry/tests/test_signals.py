from .base import *

class TestSignalsAusgabe(DataTestCase):
    
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = magazin.objects.create(magazin_name='Testmagazin')
        cls.obj1 = cls.model.objects.create(magazin=cls.mag)
        cls.monat = monat.objects.create(pk=12, monat='Dezember', abk='Dez', ordinal = 12)
        
        cls.obj2 = cls.model.objects.create(magazin=cls.mag)
        cls.obj2.ausgabe_jahr_set.create(jahr=2000)
        cls.obj2.ausgabe_num_set.create(num=12)
        cls.obj2.ausgabe_lnum_set.create(lnum=12)
        cls.obj2.ausgabe_monat_set.create(monat_id=12)
        
        cls.test_data = [cls.obj1, cls.obj2]
        
        super().setUpTestData()
    
    def setUp(self):
        super().setUp()
        # Do pending updates
        self.queryset._update_names()
        
    # post_saved signals
    def test_signal_recieved_from_ausgabe_jahr_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        ausgabe_jahr.objects.create(ausgabe=self.obj1, jahr=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_num_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        ausgabe_num.objects.create(ausgabe=self.obj1, num=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_lnum_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        ausgabe_lnum.objects.create(ausgabe=self.obj1, lnum=1)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_monat_post_saved(self):
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        ausgabe_monat.objects.create(ausgabe=self.obj1, monat_id=12)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
        
    # post_delete signals
    def test_signal_recieved_from_ausgabe_jahr_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        ausgabe_jahr.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_num_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        ausgabe_num.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_lnum_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        ausgabe_lnum.objects.filter(ausgabe=self.obj2).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
    
    def test_signal_recieved_from_ausgabe_monat_post_delete(self):
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', False)
        ausgabe_monat.objects.filter(ausgabe=self.obj2, monat_id=12).delete()
        self.assertQSValuesList(self.qs_obj2, '_changed_flag', True)
        
    # magazin signals
    def test_signal_recieved_from_magazin(self):
        self.assertAllQSValuesList(self.queryset, '_changed_flag', False)
        self.mag.save() # prompt every ausgabe of mag to update
        self.assertAllQSValuesList(self.queryset, '_changed_flag', True)
