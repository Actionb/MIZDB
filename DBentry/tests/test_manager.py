from .base import *
from DBentry.managers import CNQuerySet

class TestMIZQuerySet(DataTestCase):
    
    model = band
    raw_data = [
        {'band_name': 'Testband1', }, 
        {'band_name': 'Testband2', 'band_alias__alias':'Coffee', 'genre__genre': ['Rock']}, 
        {'band_name': 'Testband3', 'band_alias__alias':['Juice', 'Water'], 'genre__genre': ['Rock', 'Jazz']}, 
    ]
    fields = ['band_name', 'genre__genre', 'band_alias__alias']
    
    def test_values_dict(self):
        v = self.queryset.values_dict(*self.fields)
        self.assertEqual(len(v), 3)
        
        self.assertTrue(all(o.pk in v for o in self.test_data))
        
        # obj1
        d = v.get(self.obj1.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband1'])
        
        # obj2
        d = v.get(self.obj2.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband2'])
        self.assertListEqualSorted(d['genre__genre'], ['Rock'])
        self.assertListEqualSorted(d['band_alias__alias'], ['Coffee'])
        
        # obj3
        d = v.get(self.obj3.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband3'])
        self.assertListEqualSorted(d['genre__genre'], ['Rock', 'Jazz'])
        self.assertListEqualSorted(d['band_alias__alias'], ['Juice', 'Water'])
        
    def test_values_dict_num_queries(self):
        with self.assertNumQueries(1):
            v = self.queryset.values_dict(*self.fields)
        
    def test_values_dict_obj1(self):
        v = self.qs_obj1.values_dict(*self.fields)
        d = v.get(self.obj1.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband1'])
        
    def test_values_dict_obj2(self):
        v = self.qs_obj2.values_dict(*self.fields)
        d = v.get(self.obj2.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband2'])
        self.assertListEqualSorted(d['genre__genre'], ['Rock'])
        self.assertListEqualSorted(d['band_alias__alias'], ['Coffee'])
        
    def test_values_dict_obj3(self):
        v = self.qs_obj3.values_dict(*self.fields)
        d = v.get(self.obj3.pk)
        self.assertListEqualSorted(d['band_name'], ['Testband3'])
        self.assertListEqualSorted(d['genre__genre'], ['Rock', 'Jazz'])
        self.assertListEqualSorted(d['band_alias__alias'], ['Juice', 'Water'])
        
class TestMIZQuerySetAusgabe(DataTestCase):

    model = ausgabe
    fields = ausgabe.name_composing_fields
    raw_data = [
        {'magazin__magazin_name':'Testmagazin', 'sonderausgabe': True, 'beschreibung': 'Snowflake'}, 
        {'magazin__magazin_name':'Testmagazin', 'sonderausgabe': False, 'beschreibung': 'Snowflake'}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 'ausgabe_num__num': [1, 2]}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 'ausgabe_lnum__lnum': [1, 2]}, 
        {'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 'ausgabe_monat__monat__monat':['Januar', 'Februar']}, 
        {'magazin__magazin_name':'Testmagazin', 'e_datum':'2000-01-01'}, 
    ]
    
    def test_values_dict_obj1(self):
        expected = {self.obj1.pk :  {
            'beschreibung': ['Snowflake'], 
            'sonderausgabe': [True], 
        }}
        self.assertDictsEqual(self.qs_obj1.values_dict(*self.fields), expected)
    
    def test_values_dict_obj2(self):
        expected = {self.obj2.pk :  {
            'beschreibung': ['Snowflake'], 
            'sonderausgabe': [False], 
        }}
        self.assertDictsEqual(self.qs_obj2.values_dict(*self.fields), expected)
    
    def test_values_dict_obj2_include_empty(self):
        expected = {self.obj2.pk :  {
            'beschreibung': ['Snowflake'], 
            'sonderausgabe': [False], 
            'e_datum': [None], 
            'jahrgang': [None], 
            'magazin__ausgaben_merkmal': [''], 
            'ausgabe_jahr__jahr': [None], 
            'ausgabe_num__num': [None], 
            'ausgabe_lnum__lnum': [None], 
            'ausgabe_monat__monat__abk': [None]
        }}
        self.assertDictsEqual(self.qs_obj2.values_dict(*self.fields, include_empty=True), expected)
    
    def test_values_dict_obj3(self):
        expected = {self.obj3.pk :  {
            'sonderausgabe': [False], 
            'ausgabe_jahr__jahr': [2000, 2001], 
            'ausgabe_num__num': [1, 2], 
        }}
        self.assertDictsEqual(self.qs_obj3.values_dict(*self.fields), expected)
    
    def test_values_dict_obj4(self):
        expected = {self.obj4.pk :  {
            'sonderausgabe': [False], 
            'ausgabe_jahr__jahr': [2000, 2001], 
            'ausgabe_lnum__lnum': [1, 2], 
        }}
        self.assertDictsEqual(self.qs_obj4.values_dict(*self.fields), expected)
    
    def test_values_dict_obj5(self):
        expected = {self.obj5.pk :  {
            'sonderausgabe': [False], 
            'ausgabe_jahr__jahr': [2000, 2001], 
            'ausgabe_monat__monat__abk': ['Jan', 'Feb']
        }}
        self.assertDictsEqual(self.qs_obj5.values_dict(*self.fields), expected)
    
    def test_values_dict_obj6(self):
        import datetime
        expected = {self.obj6.pk :  {
            'sonderausgabe': [False], 
            'e_datum': [datetime.date(2000, 1, 1)], 
        }}
        self.assertDictsEqual(self.qs_obj6.values_dict(*self.fields), expected)
        
    
    
@tag("cn")
class TestCNQuerySet(DataTestCase):
    
    model = ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = make(magazin, magazin_name = 'Testmagazin')
        cls.obj1 = make(ausgabe, magazin=cls.mag)
        cls.obj2 = make(
            ausgabe, magazin=cls.mag, ausgabe_monat__monat__monat='Dezember', ausgabe_lnum__lnum=12, 
            ausgabe_num__num=12, ausgabe_jahr__jahr=2000
        )
        cls.test_data = [cls.obj1, cls.obj2]
        super().setUpTestData()
    
    def setUp(self):
        super().setUp()
        # Assign CNQuerySet as the manager for this TestCase
        self.queryset = CNQuerySet(self.model, query=self.queryset.query)
        self.qs_obj1 = self.queryset.filter(pk=self.obj1.pk)
        self.qs_obj2 = self.queryset.filter(pk=self.obj2.pk)
        # Do pending updates (_changed_flag set by signals, etc.)
        self.queryset._update_names()
    
    def test_update_sets_changed_flag(self):
        # update() should change the _changed_flag if it is NOT part of the update 
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        self.queryset.update(beschreibung='Test')
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , True)
        
    def test_update_not_sets_changed_flag(self):
        # update() should NOT change the _changed_flag if it is part of the update 
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        self.queryset.update(_changed_flag=False)
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        
    def test_bulk_create_sets_changed_flag(self):
        # in order to update the created instances' names on their next query/instantiation, bulk_create must include _changed_flag == True
        new_obj = ausgabe(magazin=self.mag, beschreibung='My Unique Name', sonderausgabe=True)
        self.queryset.bulk_create([new_obj])
        qs = self.queryset.filter(beschreibung='My Unique Name', sonderausgabe=True)
        self.assertAllQSValuesList(qs, '_changed_flag', True)
    
    def test_values_updates_name(self):
        # values('_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValues(self.qs_obj1, '_name', 'Testinfo')
        self.assertQSValues(self.qs_obj1, '_changed_flag', False)
        
    def test_values_not_updates_name(self):
        # values(!'_name') should NOT update the name => _changed_flag remains True
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValues(self.qs_obj1, '_changed_flag', True)
    
    def test_values_list_updates_name(self):
        # values_list('_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1, '_name', 'Testinfo')
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', False)
        
    def test_values_list_not_updates_name(self):
        # values_list(!'_name') should NOT update the name => _changed_flag remains True
        obj1_name = self.obj1._name
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1, '_changed_flag', True)

    def test_only_updates_name(self):
        # only('_name')/defer(!'_name') should return an up-to-date name
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1.only('_name'), '_changed_flag', False)
        self.assertQSValuesList(self.qs_obj1, '_name', 'Testinfo')
        
        self.qs_obj1.update(_changed_flag=True, beschreibung="Testinfo2")
        self.assertQSValuesList(self.qs_obj1.defer('id'), '_changed_flag', False)
        self.assertQSValuesList(self.qs_obj1, '_name', 'Testinfo2')
        
    def test_defer_not_updates_name(self):
        # defer('_name')/only(!'_name') should NOT return an up-to-date name => _changed_flag remains True
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertQSValuesList(self.qs_obj1.defer('_name'), '_changed_flag', True)
        self.assertQSValuesList(self.qs_obj1.only('id'), '_changed_flag', True)
        
    def test_filter_updates_names(self):
        # Make sure that .filter() updates and then searches with the updated name
        self.assertFalse(self.qs_obj1.filter(_name='Testinfo').exists())
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        self.assertTrue(self.qs_obj1.filter(_name='Testinfo').exists())
        self.assertAllQSValuesList(self.qs_obj1, '_changed_flag' , False)
        self.assertQSValuesList(self.qs_obj1, '_name', 'Testinfo')
        
    def test_update_names_num_queries_empty(self):
        self.assertAllQSValuesList(self.queryset, '_changed_flag' , False)
        with self.assertNumQueries(1):
            self.queryset._update_names()
        
    def test_update_names_num_queries(self):
        # Should be six queries: 
        # - one from querying the existence of _changed_flag records,
        # - one from calling values_dict,
        # - one each for every object to be updated,
        # - two for the transaction.atomic block
        self.queryset.update(_changed_flag=True)
        with self.assertNumQueries(6):
            self.queryset._update_names()
            
    def test_num_queries(self):
        # 3 queries for each call of _update_names from only, filter and values_list + one query for the actual list
        with self.assertNumQueries(4):
            list(self.queryset.only('_name').filter(_name='Testinfo').values_list('_name'))
        
