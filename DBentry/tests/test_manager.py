from .base import *
from DBentry.managers import *
from DBentry.query import BaseSearchQuery, PrimaryFieldsSearchQuery, ValuesDictSearchQuery

class TestMIZQuerySet(DataTestCase):
    
    model = band
    raw_data = [
        {'band_name': 'Testband1', }, 
        {'band_name': 'Testband2', 'band_alias__alias':'Coffee', 'genre__genre': ['Rock', 'Jazz']}, 
        {'band_name': 'Testband3', 'band_alias__alias':['Juice', 'Water'], 'genre__genre': ['Rock', 'Jazz']}, 
    ]
    fields = ['band_name', 'genre__genre', 'band_alias__alias']
    
    @patch.object(ValuesDictSearchQuery, 'search', return_value = ('ValuesDictSearchQuery', False))
    @patch.object(PrimaryFieldsSearchQuery, 'search', return_value = ('PrimaryFieldsSearchQuery', False))
    @patch.object(BaseSearchQuery, 'search', return_value = ('BaseSearchQuery', False))
    def test_find_strategy_chosen(self, MockBSQ, MockPFSQ, MockVDSQ):
        # Assert that 'find' chooses the correct search strategy dependent on the model's properties
        model = Mock(name_field = '', primary_search_fields = [], search_field_suffixes = {})
        model.get_search_fields.return_value = []
        qs = Mock(model = model, find = MIZQuerySet.find)
        
        self.assertEqual(qs.find(qs,'x'), 'BaseSearchQuery')
        
        model.primary_search_fields = ['Something']
        self.assertEqual(qs.find(qs, 'x'), 'PrimaryFieldsSearchQuery')
        
        model.name_field = 'Something again'
        self.assertEqual(qs.find(qs,'x'), 'ValuesDictSearchQuery')
    
    def test_find(self):
        self.assertIn((self.obj1.pk, str(self.obj1)), self.queryset.find('Testband'))
        self.assertIn((self.obj2.pk, str(self.obj2) + ' (Band-Alias)'), self.queryset.find('Coffee'))
        self.assertFalse(self.queryset.find('Jazz'))
        
    def test_values_dict(self):
        v = self.queryset.values_dict(*self.fields)
        self.assertEqual(len(v), 3)
        
        self.assertTrue(all(o.pk in v for o in self.test_data))
        
        # obj1
        expected = {'band_name': ['Testband1']}
        self.assertEqual(v.get(self.obj1.pk), expected)
        
        # obj2
        expected = {
            'band_name': ['Testband2'], 'genre__genre': ['Rock', 'Jazz'], 
            'band_alias__alias': ['Coffee']
        }
        self.assertEqual(v.get(self.obj2.pk), expected)
        
        # obj3
        expected = {
            'band_name': ['Testband3'], 'genre__genre': ['Rock', 'Jazz'], 
            'band_alias__alias': ['Juice', 'Water']
        }
        self.assertEqual(v.get(self.obj3.pk), expected)
        
    def test_values_dict_num_queries(self):
        with self.assertNumQueries(1):
            self.queryset.values_dict(*self.fields)
        
    def test_values_dict_include_empty(self):
        v = self.qs_obj1.values_dict(*self.fields, include_empty = True)
        expected = {
            'band_name': ['Testband1'], 'genre__genre': [None], 
            'band_alias__alias': [None]
        }
        self.assertEqual(v.get(self.obj1.pk), expected)
        
    def test_values_dict_tuplfy(self):
        v = self.qs_obj2.values_dict(*self.fields, tuplfy = True)
        expected = {
            'band_name': ('Testband2',), 'genre__genre': ('Rock', 'Jazz'), 
            'band_alias__alias': ('Coffee',)
        }
        self.assertEqual(v.get(self.obj2.pk), expected)
        
    def test_values_dict_flatten(self):
        v = self.qs_obj3.values_dict(*self.fields, flatten = True)
        expected = {
            'band_name': 'Testband3', 'genre__genre': ['Rock', 'Jazz'], 
            'band_alias__alias': ['Juice', 'Water']
        }
        self.assertEqual(v.get(self.obj3.pk), expected)
        
    def test_values_dict_flatten_no_flds(self):
        v = self.qs_obj1.values_dict(flatten = True)
        d = v.get(self.obj1.pk)
        self.assertEqual(d, {'band_name': 'Testband1'})
        
    def test_values_dict_pk_in_flds(self):
        v = self.qs_obj1.values_dict('band_name', 'pk')
        self.assertIn(self.obj1.pk, v)
   
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
        
class BuchQuerySet(DataTestCase):
    
    model = buch
    raw_data = [
        {'ISBN': '978-1-234-56789-7', 'EAN': '73513537'}, 
        {'ISBN': '978-4-56-789012-0', 'EAN': "1234567890128"}
    ]
    
    def test_filter_finds_isbn(self):
        isbn_10 = "123456789X"
        self.assertIn(self.obj1, self.queryset.filter(ISBN=isbn_10))
        isbn_10 = "1-234-56789-X"
        self.assertIn(self.obj1, self.queryset.filter(ISBN=isbn_10))
        
        isbn_13 = '9784567890120'
        self.assertIn(self.obj2, self.queryset.filter(ISBN=isbn_13))
        isbn_13 = '978-4-56-789012-0'
        self.assertIn(self.obj2, self.queryset.filter(ISBN=isbn_13))
        
    def test_filter_finds_ean(self):
        ean_8 = '7351-3537'
        self.assertIn(self.obj1, self.queryset.filter(EAN=ean_8))
        ean_13 = '1-234567-890128'
        self.assertIn(self.obj2, self.queryset.filter(EAN=ean_13))
