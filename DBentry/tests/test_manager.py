from .base import *
from DBentry.managers import CNQuerySet

class TestMIZQuerySet(DataTestCase):
    pass
    
    
class TestCNQuerySet(AusgabeSimpleDataMixin, DataTestCase):
    
    manager_class = CNQuerySet
    
    def setUp(self):
        super().setUp()
        self.queryset = CNQuerySet(self.model)
        self.qs_obj1 = self.queryset.filter(pk=self.obj1.pk)
        self.qs_obj2 = self.queryset.filter(pk=self.obj2.pk)
    
    def test_update_sets_changed_flag(self):
        # update() should change the _changed_flag if it is NOT part of the update 
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        self.queryset.update(info='Test')
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , True)
        
    def test_update_not_sets_changed_flag(self):
        # update() should NOT change the _changed_flag if it is part of the update 
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        self.queryset.update(_changed_flag=False)
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        
    def test_bulk_create_sets_changed_flag(self):
        # in order to update the created instances' names on their **next** instantiation, bulk_create must include _changed_flag == True
        new_obj = ausgabe(magazin=self.mag, info='My Unique Name', sonderausgabe=True)
        self.assertFalse(new_obj._name == 'My Unique Name')
        self.queryset.bulk_create([new_obj])
        qs = self.queryset.filter(info='My Unique Name', sonderausgabe=True)
        self.assertAllQSValuesList(qs, '_changed_flag', True)
        self.assertEqual(str(qs.first()), 'My Unique Name')
    
    def test_values_updates_name(self):
        # values('_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertQSValues(self.qs_obj1, '_name', 'Testinfo')
        self.assertQSValues(self.qs_obj1, '_changed_flag', False)
        
    def test_values_not_updates_name(self):
        # values(!'_name') should NOT update the name => _changed_flag remains True
        obj1_name = self.obj1._name
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertQSValues(self.qs_obj1, '_changed_flag', True)
    
    def test_values_list_updates_name(self):
        # values_list('_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1, '_name', 'Testinfo')
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        
    def test_values_list_not_updates_name(self):
        # values_list(!'_name') should NOT update the name => _changed_flag remains True
        obj1_name = self.obj1._name
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)
        
    def test_only_updates_name(self):
        # only('_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertFalse(self.qs_obj1.only('_name').first()._changed_flag)
        
    def test_defer_not_updates_name(self):
        # defer('_name') should NOT return an up-to-date name => _changed_flag remains True
        self.qs_obj1.update(_changed_flag=True, info='Testinfo', sonderausgabe=True)
        self.assertTrue(self.qs_obj1.defer('_name').first()._changed_flag)
        
