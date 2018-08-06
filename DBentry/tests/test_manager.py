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
        { # obj1: nr 2 by chronologic_order
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'ausgabe_monat__monat__ordinal':[9, 10], 'ausgabe_lnum__lnum': [55]
        },
        { # obj2: 6 
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 
            'ausgabe_monat__monat__ordinal':[12, 1], 'ausgabe_num__num': [1, 12]
        }, 
        { # obj3: 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'ausgabe_monat__monat__ordinal':[9], 'ausgabe_num__num': [9]
        }, 
        { # obj4: 5
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'ausgabe_monat__monat__ordinal':[11, 12], 'ausgabe_lnum__lnum': [56]
        },  
        { # obj5: 3
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000],
            'ausgabe_monat__monat__ordinal':[10], 'ausgabe_num__num': [10]
        }, 
        { # obj6: 4
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'ausgabe_monat__monat__ordinal':[11], 'ausgabe_num__num': [11]
        }, 
    ]
    
    def setUp(self):
        super().setUp()
        self.queryset = self.model.objects.filter(pk__in=self._ids)
        self.ordered_ids = [self.obj3.pk, self.obj1.pk, self.obj5.pk, self.obj6.pk, self.obj4.pk, self.obj2.pk]
        
    def test_chronologic_order(self):
        # Assert that no expensive ordering is being done on an empty or unfiltered queryset.
        self.assertEqual(self.queryset.none().chronologic_order().query.order_by, ['pk'])
        self.assertEqual(self.model.objects.chronologic_order().query.order_by, ['pk'])
        
        self.assertPKListEqual(self.queryset, self._ids)
        
        expected_order_by = [
            'magazin', 'jahr', 'sonderausgabe', 'monat', 'num', 'lnum', 'e_datum', 'pk'
        ]
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected_order_by)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = self.queryset.chronologic_order(ordering = [])
        self.assertEqual(qs.query.order_by, expected_order_by)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = self.queryset.chronologic_order(ordering = ['pk'])
        self.assertEqual(qs.query.order_by, expected_order_by)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = self.queryset.chronologic_order(ordering = ['-pk'])
        self.assertEqual(qs.query.order_by, expected_order_by[:-1] + ['-pk'])
        self.assertPKListEqual(qs, self.ordered_ids)
        
        expected = [
            '-magazin', 'sonderausgabe', 'jahr', 'monat', 'num', 'lnum', 'e_datum', 'pk'
        ]
        qs = self.queryset.chronologic_order(ordering = ['-magazin', 'sonderausgabe', 'jahr'])
        self.assertEqual(qs.query.order_by, expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        # Introduce a missing jahr in one of the objects; as long as the amount of missing jahr is smaller 
        # than missing jahrgang, nothing should change
        self.obj6.ausgabe_jahr_set.all().delete()
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected_order_by)
        
        # Have as many missing jahr as missing jahrgang; both should be removed from ordering
        self.obj5.ausgabe_jahr_set.all().delete()
        self.obj4.ausgabe_jahr_set.all().delete()
        self.queryset.filter(pk__in=[self.obj1.pk, self.obj2.pk, self.obj3.pk]).update(jahrgang = 1)
        expected = [
            'magazin', 'sonderausgabe', 'monat', 'num', 'lnum', 'e_datum', 'pk'
        ]
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected)
        
        # Have more jahr missing than jahrgang; jahr should be removed
        self.qs_obj4.update(jahrgang = 1)
        expected.insert(1, 'jahrgang')
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected)
        
        # Have all objects with jahrgang but no jahr; only jahrgang should be in ordering
        self.obj1.ausgabe_jahr_set.all().delete()
        self.obj2.ausgabe_jahr_set.all().delete()
        self.obj3.ausgabe_jahr_set.all().delete()
        self.queryset.update(jahrgang = 1)
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected)
    
    def test_find_order(self):
        result_ids = [i[0] for i in self.queryset.chronologic_order().find('2000')]
        self.assertEqual(result_ids, self.ordered_ids)
        
        # find() will return a list of [exact_matches] + [startswith_matches] + [contains_matches]
        # the individual sublists will be ordered by primary key
        expected = [self.obj2.pk, self.obj3.pk, self.obj5.pk, self.obj6.pk, self.obj1.pk, self.obj4.pk]
        result_ids = [i[0] for i in self.queryset.find('2000', ordered = False)]
        self.assertEqual(result_ids, expected)
    
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
