import random
from itertools import chain
from unittest.mock import patch, Mock

from .base import DataTestCase

from django.test import tag
from django.db.models.query import QuerySet

import DBentry.models as _models
from DBentry.factory import make
from DBentry.managers import CNQuerySet, MIZQuerySet
from DBentry.query import BaseSearchQuery, PrimaryFieldsSearchQuery, ValuesDictSearchQuery

class TestMIZQuerySet(DataTestCase):
    
    model = _models.band
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

class TestAusgabeQuerySet(DataTestCase):

    model = _models.ausgabe
    fields = model.name_composing_fields
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
        self.ordered_ids = [self.obj3.pk, self.obj1.pk, self.obj5.pk, self.obj6.pk, self.obj4.pk, self.obj2.pk]

    def test_chronologic_order(self):
        # Assert that no expensive ordering is being done on an empty or on a queryset with more than one magazin.
        default_ordering = self.model._meta.ordering
        queryset = self.model.objects.filter(pk__in=self._ids)
        self.assertEqual(queryset.none().chronologic_order().query.order_by, default_ordering)
        make(_models.ausgabe, magazin__magazin_name = 'Bad') # make ausgabe with a new, different magazin
        self.assertEqual(self.model.objects.chronologic_order().query.order_by, default_ordering)
        
        expected = [
            'magazin', 'jahr', 'jahrgang', 'sonderausgabe', 'monat', 'num', 'lnum', 'e_datum', '-pk'
        ]
        qs = queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = queryset.chronologic_order(ordering = [])
        self.assertEqual(qs.query.order_by, expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = queryset.chronologic_order(ordering = ['pk'])
        self.assertEqual(qs.query.order_by, expected[:-1] + ['pk'])
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = queryset.chronologic_order(ordering = ['-pk'])
        self.assertEqual(qs.query.order_by, expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
        qs = queryset.chronologic_order(ordering = ['-magazin', 'sonderausgabe', 'jahr'])
        self.assertEqual(qs.query.order_by, ['-magazin', 'sonderausgabe', 'jahr'] + expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
    def test_chronologic_order_jahrgang_over_jahr(self):
        # Have more objects with jahrgang than jahr; jahrgang should take priority
        _models.ausgabe_jahr.objects.all().delete()
        self.qs_obj4.update(jahrgang = 1)
        
        expected = [
            'magazin', 'jahrgang', 'jahr', 'sonderausgabe', 'monat', 'num', 'lnum', 'e_datum', '-pk'
        ]
        qs = self.queryset.chronologic_order()
        self.assertEqual(qs.query.order_by, expected)
        
    def test_chronologic_order_criteria_equal(self):
        # If none of the four criteria dominate, the default order should be:
        # num, monat, lnum, e_datum
        _models.ausgabe_monat.objects.all().delete()
        _models.ausgabe_num.objects.all().delete()
        _models.ausgabe_lnum.objects.all().delete()
        expected = [
            'magazin', 'jahr', 'jahrgang', 'sonderausgabe', 'num', 'monat', 'lnum', 'e_datum', '-pk'
        ]
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
        
    def test_update_names_after_chronologic_order(self):
        # Assert that resetting ordering for _update_names does not break the ordering of the underlying queryset.
        expected = [
            'magazin', 'jahr', 'jahrgang', 'sonderausgabe', 'monat', 'num', 'lnum', 'e_datum', '-pk'
        ]
        qs = self.queryset.chronologic_order()
        qs._update_names()
        self.assertEqual(qs.query.order_by, expected)
        self.assertPKListEqual(qs, self.ordered_ids)
        
    def test_keeps_chronologically_ordered_value_after_cloning(self):
        qs = self.queryset
        self.assertFalse(qs.chronologically_ordered)
        self.assertFalse(qs._clone().chronologically_ordered)
        
        qs = qs.chronologic_order()
        self.assertTrue(qs.chronologically_ordered)
        self.assertTrue(qs._clone().chronologically_ordered)
        self.assertFalse(self.queryset.chronologically_ordered) # just to make sure I didnt alter the class wide attribute... common gotcha
        
    def test_chronologic_order_does_not_order_twice(self):
        # Assert that chronologic_order does not try to create a chronologic order if it's already *chronologically* ordered.
        # To check, we mock annotate(), because that method is only called when establishing a new order.
        qs = self.queryset.order_by()
        with patch.object(qs, 'annotate') as mocked_annotate:
            qs = qs.chronologic_order()
            self.assertNotEqual(mocked_annotate.call_count, 0)
        
        # Patch twice to reset the mock
        with patch.object(qs, 'annotate') as mocked_annotate:
            qs.chronologic_order()
            self.assertEqual(mocked_annotate.call_count, 0)
            
    def test_order_by_call_disables_chronologic_order(self):
        # A call of order_by should set chronologically_ordered to False.
        qs = self.queryset.chronologic_order()
        self.assertTrue(qs.chronologically_ordered)
        qs = qs.order_by('magazin')
        self.assertFalse(qs.chronologically_ordered)
        
class TestAusgabeIncrementJahrgang(DataTestCase):
    
    model = _models.ausgabe
    
    raw_data = [
        { # obj1: start_jg
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'e_datum': '2000-06-01', 'ausgabe_monat__monat__ordinal': [6], 'ausgabe_num__num' : [6], 
        }, 
        { # obj2: start_jg - 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000], 
            'e_datum': '2000-05-01', 'ausgabe_monat__monat__ordinal': [5], 'ausgabe_num__num' : [5], 
        }, 
        { # obj3: start_jg - 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [1999], 
            'e_datum': '1999-06-01', 'ausgabe_monat__monat__ordinal': [6], 'ausgabe_num__num' : [6], 
        }, 
        { # obj4: start_jg
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2000, 2001], 
            'e_datum': '2000-12-31', 'ausgabe_monat__monat__ordinal': [12, 1], 'ausgabe_num__num' : [12, 1], 
        }, 
        { # obj5: start_jg
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001], 
            'e_datum': '2001-05-01', 'ausgabe_monat__monat__ordinal': [5], 'ausgabe_num__num' : [5], 
        }, 
        { # obj6: start_jg + 1
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2001], 
            'e_datum': '2001-06-01', 'ausgabe_monat__monat__ordinal': [6], 'ausgabe_num__num' : [6], 
        }, 
        { # obj7: start_jg + 2
            'magazin__magazin_name':'Testmagazin', 'ausgabe_jahr__jahr': [2002], 
            'e_datum': '2002-06-01', 'ausgabe_monat__monat__ordinal': [6], 'ausgabe_num__num' : [6], 
        }, 
        { # obj8: ignored
            'magazin__magazin_name':'Testmagazin', 'ausgabe_monat__monat__ordinal': [6], 
            'ausgabe_num__num' : [6]
        }, 
    ]
    
    def assertIncrementedUpdateDict(self, update_dict):
        self.assertEqual(len(update_dict), 4, msg = str(update_dict))
        
        self.assertIn(9, update_dict)
        self.assertEqual(update_dict[9], [self.obj2.pk, self.obj3.pk])
        
        self.assertIn(10, update_dict)
        self.assertEqual(update_dict[10], [self.obj1.pk, self.obj4.pk, self.obj5.pk])
        
        self.assertIn(11, update_dict)
        self.assertEqual(update_dict[11], [self.obj6.pk])
        
        self.assertIn(12, update_dict)
        self.assertEqual(update_dict[12], [self.obj7.pk])
        
    def assertIncrementedQuerySet(self, queryset):
        self.assertEqual(queryset.get(pk=self.obj1.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj2.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj3.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj4.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj5.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj6.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj7.pk).jahrgang, 12)
        self.assertEqual(queryset.get(pk=self.obj8.pk).jahrgang, None)        
    
    def test_increment_by_date(self):
        update_dict = self.queryset.increment_jahrgang(start_obj = self.obj1, start_jg = 10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)
        
    def test_increment_by_month(self):
        self.queryset.update(e_datum = None)
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj = self.obj1, start_jg = 10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)
        
    def test_increment_by_num(self):
        self.queryset.update(e_datum = None)
        _models.ausgabe_monat.objects.all().delete()
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj = self.obj1, start_jg = 10)
        self.assertIncrementedUpdateDict(update_dict)
        self.assertIncrementedQuerySet(self.queryset)
        
    def test_increment_by_year(self):
        self.queryset.update(e_datum = None)
        _models.ausgabe_monat.objects.all().delete()
        _models.ausgabe_num.objects.all().delete()
        self.obj1.refresh_from_db()
        update_dict = self.queryset.increment_jahrgang(start_obj = self.obj1, start_jg = 10)
        
        self.assertEqual(len(update_dict), 4, msg = str(update_dict))
        
        self.assertIn(9, update_dict)
        self.assertEqual(update_dict[9], [self.obj3.pk])
        
        self.assertIn(10, update_dict)
        self.assertEqual(update_dict[10], [self.obj1.pk, self.obj2.pk, self.obj4.pk])
        
        self.assertIn(11, update_dict)
        self.assertEqual(update_dict[11], [self.obj5.pk, self.obj6.pk])
        
        self.assertIn(12, update_dict)
        self.assertEqual(update_dict[12], [self.obj7.pk])
        
        queryset = self.queryset
        self.assertEqual(queryset.get(pk=self.obj1.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj2.pk).jahrgang, 10) 
        self.assertEqual(queryset.get(pk=self.obj3.pk).jahrgang, 9)
        self.assertEqual(queryset.get(pk=self.obj4.pk).jahrgang, 10)
        self.assertEqual(queryset.get(pk=self.obj5.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj6.pk).jahrgang, 11)
        self.assertEqual(queryset.get(pk=self.obj7.pk).jahrgang, 12)
        self.assertEqual(queryset.get(pk=self.obj8.pk).jahrgang, None)  
        
    def test_increment_mixed(self):
        #TODO: test_increment_mixed
        pass
        
@tag("slow")
class TestAusgabeQuerySetOrdering(DataTestCase):
    model = _models.ausgabe
    
    @classmethod
    def setUpTestData(cls):
        possible_pks = list(range(1, 1001))
        def get_random_pk():
            # 'randomize' the pk values so we cannot rely on them for ordering
            return possible_pks.pop(random.randrange(0, len(possible_pks)-1))
        
        cls.nums = []
        cls.lnums = []
        cls.monate = []
        cls.jgs = []
        cls.mag = make(_models.magazin)
        
        for jg, year in enumerate(range(1999, 2005), start = 1):
            for i in range(1, 13):
                cls.nums.append(make(cls.model, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_num__num = i, ausgabe_jahr__jahr = year
                ))
                cls.lnums.append(make(cls.model, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_lnum__lnum = i, ausgabe_jahr__jahr = year
                ))
                cls.monate.append(make(cls.model, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_monat__monat__ordinal = i, ausgabe_jahr__jahr = year
                ))
                cls.jgs.append(make(cls.model, 
                    pk = get_random_pk(), magazin = cls.mag, ausgabe_num__num = i, jahrgang = jg
                ))
        cls.all = cls.nums + cls.lnums + cls.monate + cls.jgs
        super().setUpTestData()
        
    def setUp(self):
        # We do not need the 'qs_objX' attribute TestDataMixin.setUp would create for us.
        # By not having an empty test_data attribute, TestDataMixin will skip that part, reducing db hits.
        for o in self.all:
            o.refresh_from_db()
        super().setUp
    
    def get_search_results(self, qs, q):
        result = qs.find(q)
        if isinstance(result, QuerySet):
            return list(result.values_list('_name', flat = True))
        return [tpl[1] for tpl in result]
        
    def filter(self, _list, qs):
        filtered = qs.values_list('pk', flat = True)
        return [o._name for o in _list if o.pk in filtered]
        
    def assertOrderingEqual(self, a, b):
        # Might be faster..?
        if len(a) != len(b):
            raise AssertionError()
        for i in range(len(a)-1):
            if a[i] != b[i]:
                raise AssertionError()
    
    def test_ordering_mixed(self):
        # If no criteria (num, lnum, monat) dominates over the others, the general order should be:
        # lnum, monat, num
        # the queryset needs to be filtered or chronologic_order will take a short cut
        queryset = self.model.objects.filter(pk__in = [o.pk for o in chain(self.lnums, self.monate, self.nums)]).chronologic_order() 
        qs = self.model.objects.filter(ausgabe_jahr__jahr=2001)
        expected = self.filter(self.lnums, qs) + self.filter(self.monate, qs) + self.filter(self.nums, qs)
        self.assertEqual(self.get_search_results(queryset, '2001'), expected)
        
        # num dominant
        
        # lnum dominant
        
        # monat dominant
        
        # if jahr and jahrgang are present in the search results:
        # pick the one that is most dominant or neither if both are equally presented
        
        # jahr dominant:
        # --> any records with jahrgang and no jahr will be at the top
        filtered = list(_models.ausgabe_lnum.objects.filter(lnum=11).values_list('ausgabe_id', flat = True))
        filtered += list(_models.ausgabe_num.objects.filter(num=11).values_list('ausgabe_id', flat = True))
        
        queryset = self.model.objects.filter(pk__in = filtered).chronologic_order()
        expected = self.filter(self.jgs, queryset) 
        for num, lnum in zip(self.nums, self.lnums):
            if lnum.pk in filtered:
                expected.append(lnum._name)
            if num.pk in filtered:
                expected.append(num._name)
            
        self.assertEqual(list(queryset.values_list('_name', flat = True)), expected)
        self.assertEqual(self.get_search_results(queryset, '11'), expected)
        
        # jahrgang dominant: 
        # --> any records with jahr and no jahrgang will be at the top
        ids = [
           o.pk for o in chain(self.nums[3:] + self.jgs)
           if o.pk in _models.ausgabe_num.objects.filter(num=11).values_list('ausgabe_id')
        ]
        
        queryset = self.model.objects.filter(pk__in = ids).chronologic_order()
        expected = self.filter(self.nums[3:] + self.jgs, queryset)
        self.assertEqual(list(queryset.values_list('_name', flat = True)), expected)
        self.assertEqual(self.get_search_results(queryset, '11'), expected)
        
    def test_ordering_num(self):
        queryset = self.model.objects.filter(pk__in=[o.pk for o in self.nums]).chronologic_order()
        
        expected = [o.pk for o in self.nums]
        self.assertEqual(list(queryset.values_list('pk', flat = True)), expected)
        
        expected = self.filter(self.nums, queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(queryset, '2001'), expected)
        
        expected = self.filter(self.nums, queryset.filter(ausgabe_num__num=11)) 
        self.assertEqual(self.get_search_results(queryset, '11'), expected)
        
    def test_ordering_lnum(self):
        queryset = self.model.objects.filter(pk__in=[o.pk for o in self.lnums]).chronologic_order()
        
        expected = [o.pk for o in self.lnums]
        self.assertEqual(list(queryset.values_list('pk', flat = True)), expected)
        
        expected = self.filter(self.lnums, queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(queryset, '2001'), expected)
        
        expected = self.filter(self.lnums, queryset.filter(ausgabe_lnum__lnum=11)) 
        self.assertEqual(self.get_search_results(queryset, '11'), expected)
        
    def test_ordering_monate(self):
        queryset = self.model.objects.filter(pk__in=[o.pk for o in self.monate]).chronologic_order()
        
        expected = [o.pk for o in self.monate]
        self.assertEqual(list(queryset.values_list('pk', flat = True)), expected)
        
        expected = self.filter(self.monate, queryset.filter(ausgabe_jahr__jahr=2001))
        self.assertEqual(self.get_search_results(queryset, '2001'), expected)
        
        expected = self.filter(self.monate, queryset.filter(ausgabe_monat__monat__abk='Nov')) 
        self.assertEqual(self.get_search_results(queryset, 'Nov'), expected)
    
    def test_ordering_jg(self):
        queryset = self.model.objects.filter(pk__in=[o.pk for o in self.jgs]).chronologic_order()
        
        expected = [o.pk for o in self.jgs]
        self.assertEqual(list(queryset.values_list('pk', flat = True)), expected)
        
        expected = self.filter(self.jgs, queryset.filter(jahrgang=2))
        self.assertEqual(self.get_search_results(queryset, 'Jg. 2'), expected)
        
        expected = self.filter(self.jgs, queryset.filter(ausgabe_num__num=11))
        self.assertEqual(self.get_search_results(queryset, '11'), expected)
        
    
@tag("cn")
class TestCNQuerySet(DataTestCase):
    
    model = _models.ausgabe
    
    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.magazin, magazin_name = 'Testmagazin')
        cls.obj1 = make(cls.model, magazin=cls.mag)
        cls.obj2 = make(
            cls.model, magazin=cls.mag, ausgabe_monat__monat__monat='Dezember', ausgabe_lnum__lnum=12, 
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
        new_obj = self.model(magazin=self.mag, beschreibung='My Unique Name', sonderausgabe=True)
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
        
class TestBuchQuerySet(DataTestCase):
    
    model = _models.buch
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
