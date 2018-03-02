from .base import *

from DBentry.query import *

class StrategyTestCase(DataTestCase):
    
    model = band
    search_fields = ['band_name', 'band_alias__alias', 'musiker__kuenstler_name', 'musiker__musiker_alias__alias']
    suffix = {'band_alias__alias':'Band-Alias', 'musiker__kuenstler_name':'Band-Mitglied', 'musiker__musiker_alias__alias':'Mitglied-Alias'}
    primary_search_fields = ['band_name', 'band_alias__alias']
    name_field = 'band_name'
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = band.objects.create(band_name="Guns 'N Roses")
        cls.obj1.band_alias_set.create(alias="Guns and Roses")
        
        cls.obj2 = band.objects.create(band_name='AC/DC') # can only be found via 'Axl' when searching 'Rose'
        cls.obj2.band_alias_set.create(alias="ACDC")
        
        cls.obj3 = band.objects.create(band_name="Rolling Stones") # never found
        
        cls.obj4 = band.objects.create(band_name="Rosewood") # startsw Rose
        
        cls.obj5 = band.objects.create(band_name='More Roses') # contains Rose
        
        cls.obj6 = band.objects.create(band_name='Beep')
        cls.obj6.band_alias_set.create(alias="Booproses") # alias icontains Rose
        
        cls.axl = musiker.objects.create(kuenstler_name='Axl Rose')
        cls.axl.musiker_alias_set.create(alias='Axel Rose')
        m2m_band_musiker.objects.create(musiker=cls.axl, band=cls.obj1)
        m2m_band_musiker.objects.create(musiker=cls.axl, band=cls.obj2)
        
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4, cls.obj5, cls.obj6, cls.axl]
        
        super().setUpTestData()
        
    def append_suffix(self, strat, obj, search_field, lookup):
        return strat.append_suffix(obj, search_field, lookup)
        
    def strat(self, queryset=None, search_fields = None, suffix = None, **kwargs):
        queryset = queryset or self.queryset
        search_fields = search_fields or self.search_fields
        suffix = suffix or self.suffix
        return self.strat_class(queryset, search_fields=search_fields, suffix=suffix, **kwargs)

class TestBaseStrategy(StrategyTestCase):
    
    strat_class = BaseStrategy
    
    def test_get_queryset(self):
        q = 'Rose'
        # Unfiltered
        expected = list(self.queryset.values_list('pk', flat=True))
        self.assertQSValuesList(self.strat(pre_filter=False).get_queryset(q), 'pk', expected)
        
        # Filtered
        expected = list(self.queryset.exclude(band_name='Rolling Stones').values_list('pk', flat=True))
        self.assertQSValuesList(self.strat(pre_filter=True).get_queryset(q), 'pk', expected)
        
    def test_get_suffix(self):
        self.assertEqual(self.strat().get_suffix('musiker__musiker_alias__alias'), 'Mitglied-Alias')
        new_suffix = self.suffix.copy()
        new_suffix['band_name__icontains'] = 'Tested!'
        self.assertEqual(self.strat(suffix=new_suffix).get_suffix('band_name', '__icontains'), 'Tested!')
        
    def test_append_suffix(self):
        expected = [(self.obj2.pk,"AC/DC (Band-Alias)")]
        self.assertEqual(self.strat().append_suffix([self.obj2], 'band_alias__alias'), expected)
        self.assertEqual(self.strat().append_suffix([self.obj2], 'not_in_suffixes'), [self.obj2]) #TODO: return value might change
        
    def test_do_lookup(self):
        q = 'Axel Rose'
        lookup = '__icontains'
        search_field = 'musiker__musiker_alias__alias'
        expected = [(self.obj1.pk, "Guns 'N Roses (Mitglied-Alias)"), (self.obj2.pk, "AC/DC (Mitglied-Alias)")]
        strat = self.strat()
        self.assertListEqualSorted(strat._do_lookup(lookup, search_field, q), expected)
        self.assertListEqualSorted(list(strat.ids_found), [self.obj1.pk, self.obj2.pk])
        
    def test_exact_search(self):
        lookup = '__iexact'
        
        q = 'AC/DC'
        expected = []
        strat = self.strat()
        self.assertListEqualSorted(strat.exact_search('band_alias__alias', q), expected)
        self.assertFalse(strat.exact_match)
        
        q = 'AC/DC'
        strat = self.strat()
        search_field = 'band_name'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.exact_search(search_field, q), expected)
        self.assertTrue(strat.exact_match)
        
        q = 'ACDC'
        strat = self.strat()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.exact_search(search_field, q), expected)
        self.assertTrue(strat.exact_match)
        
        q = 'Axl Rose'
        strat = self.strat()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.exact_search(search_field, q), expected)
        self.assertTrue(strat.exact_match)
        
        q = 'Axel Rose'
        strat = self.strat()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.exact_search(search_field, q), expected)
        self.assertTrue(strat.exact_match)
        
    def test_startsw_search(self):
        lookup = '__istartswith'
        
        q = 'AC/DCS'
        expected = []
        self.assertListEqualSorted(self.strat().startsw_search('band_name', q), expected)
        
        q = 'AC/'
        strat = self.strat()
        search_field = 'band_name'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.startsw_search(search_field, q), expected, msg="strat: {}".format(strat))
        
        q = 'ACD'
        strat = self.strat()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.startsw_search(search_field, q), expected)
        
        q = 'Axl'
        strat = self.strat()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.startsw_search(search_field, q), expected)
        
        q = 'Axel'
        strat = self.strat()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.startsw_search(search_field, q), expected)
        
    def test_contains_search(self):
        lookup = '__icontains'
        
        q = 'AC/DCS'
        expected = []
        self.assertListEqualSorted(self.strat().contains_search('band_name', q), expected)
        
        q = 'C/D'
        strat = self.strat()
        search_field = 'band_name'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.contains_search(search_field, q), expected)
        
        #['band_name', 'band_alias__alias', 'musiker__kuenstler_name', 'musiker__musiker_alias__alias']
        q = 'CD'
        strat = self.strat()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.contains_search(search_field, q), expected)
        
        q = 'xl R'
        strat = self.strat()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.contains_search(search_field, q), expected)
        
        q = 'xel R'
        strat = self.strat()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(strat, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(strat.contains_search(search_field, q), expected)
        
    def test_search(self):
        def extract_ids(search_results):
            ids = []
            for result in search_results:
                if isinstance(result, tuple):
                   ids.append(result[0]) 
                else:
                    ids.append(result.pk)
            return ids
            
        q = 'Rose'
        search_results, exact_match = self.strat().search(q)
        expected = list(self.queryset.exclude(band_name='Rolling Stones').values_list('pk', flat=True))
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertFalse(exact_match)
        
        q = 'Roses'
        search_results, exact_match = self.strat().search(q)
        expected = [self.obj1.pk, self.obj5.pk, self.obj6.pk]
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertFalse(exact_match)
        
        q = 'AC/DC'
        search_results, exact_match = self.strat().search(q)
        expected = [self.obj2.pk]
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertTrue(exact_match)
        
    def test_search_returns_qs_on_no_q(self):
        search_results, exact_match = self.strat().search(q=None)
        expected = list(self.queryset.values_list('pk', flat=True))
        self.assertQSValuesList(search_results, 'pk', expected)
        
    def test_search_caching(self):
        pass
    
class TestPrimStrategy(TestBaseStrategy):
    
    strat_class = PrimaryFieldsStrategy
    
    def strat(self, primary_search_fields=None, **kwargs):
        primary_search_fields = primary_search_fields or self.primary_search_fields
        return super().strat(primary_search_fields=primary_search_fields, **kwargs)
        
    def test_get_separator(self):
        q = 'Test'
        sep = self.strat().get_separator(q)
        self.assertEqual(sep, '------- weak hits for "Test" -------')
        
        # with separator_text argument
        separator_text = 'Beep boop "{q}"'
        sep = self.strat().get_separator(q, separator_text)
        self.assertEqual(sep, '--------- Beep boop "Test" ---------')
        
    def test_exact_search(self):
        # exact_match should stay False if exact_matches for secondary search fields were found
        q = 'Axl'
        strat = self.strat()
        search_field = 'musiker__kuenstler_name'
        strat.exact_search(search_field, q)
        self.assertFalse(strat.exact_match)
        
        q = 'ACDC'
        strat = self.strat()
        search_field = 'band_alias__alias'
        strat.exact_search(search_field, q)
        self.assertTrue(strat.exact_match)
        
    def test_search(self):
        # Check that the results are ordered according to the _search strategy
        
        rose_band = band.objects.create(band_name='Rose')
        some_other_band = band.objects.create(band_name='Boop')
        rose_musiker = musiker.objects.create(kuenstler_name='Rose')
        m2m_band_musiker.objects.create(musiker=rose_musiker, band=some_other_band)
        
        yet_another_band = band.objects.create(band_name='NoName')
        rose_musiker2 = musiker.objects.create(kuenstler_name='Roseman')
        m2m_band_musiker.objects.create(musiker=rose_musiker2, band=yet_another_band)
        
        q = 'Rose'
        strat= self.strat()
        search_results, exact_match = strat.search(q)
        
        self.assertEqual(len(search_results), 9)
        
        # Exact primary field match first
        lookup = '__iexact'
        search_field = 'band_name'
        expected = self.append_suffix(strat, [rose_band], search_field, lookup)
        self.assertEqual([search_results[0]], expected)
        
        # Primary startsw matches next
        lookup = '__istartswith'
        search_field = 'band_name'
        expected = self.append_suffix(strat, [self.obj4], search_field, lookup)
        self.assertEqual([search_results[1]], expected)
        
        # Then primary contains matches
        lookup = '__istartswith'
        search_field = 'band_name'
        expected = self.append_suffix(strat, [self.obj1, self.obj5], search_field, lookup)
        self.assertEqual(search_results[2:4], expected)
        
        lookup = '__istartswith'
        search_field = 'band_alias__alias'
        expected = self.append_suffix(strat, [self.obj6], search_field, lookup)
        self.assertEqual([search_results[4]], expected)
        
        # Then secondary exact_matches
        lookup = '__iexact'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [some_other_band], search_field, lookup)
        self.assertEqual([search_results[5]], expected)
        
        # Then secondary startsw matches
        lookup = '__istartswith'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [yet_another_band], search_field, lookup)
        self.assertEqual([search_results[6]], expected)
        
        # Finally, weak hits --- a separator followed by secondary contains matches
        self.assertEqual(search_results[7], (0, strat.get_separator(q)))
        lookup = '__icontains'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(strat, [self.obj2], search_field, lookup)
        self.assertEqual([search_results[8]], expected)
        
    
class TestNameStrategy(TestPrimStrategy):
    
    strat_class = NameFieldStrategy
    
    def strat(self, name_field=None, **kwargs):
        name_field = name_field or self.name_field
        return super().strat(name_field=name_field, **kwargs)#, primary_search_fields=self.primary_search_fields)
        
    def append_suffix(self, strat, obj, search_field, lookup):
        tuple_list = [(o.pk, getattr(o, self.name_field)) for o in obj]
        return strat.append_suffix(tuple_list, search_field, lookup)
        
    def test_init(self):
        # Set name_field from primary_search_fields or seconary_search_fields
        self.assertEqual(self.strat(name_field = '').name_field, 'band_name')
        self.assertEqual(self.strat(primary_search_fields=[]).name_field, 'band_name')
        
    def test_append_suffix(self):
        # expects a list of tuples --- tuple_list, field, lookup=''
        expected = [(self.obj2.pk, 'AC/DC (Band-Alias)')]
        self.assertEqual(self.strat().append_suffix(tuple_list=[(self.obj2.pk, 'AC/DC')], field='band_alias__alias'), expected)
    
class TestVDStrategy(TestNameStrategy):
    
    strat_class = ValuesDictStrategy
    
    def strat(self, values_dict=None, **kwargs):
        strat = super().strat(**kwargs)
        strat.values_dict = values_dict or self.queryset.values_dict(*self.search_fields) 
        return strat
        
    def append_suffix(self, strat, obj, search_field, lookup):
        rslt = []
        for o in obj:
            rslt.extend(strat.append_suffix(o.pk, getattr(o, self.name_field), search_field, lookup))
        return rslt
        
    def test_append_suffix(self):
        # expects two arguments over the usual one --- pk, name, field, lookup=''
        expected = [(self.obj2.pk, 'AC/DC (Band-Alias)')]
        self.assertEqual(self.strat().append_suffix(pk=self.obj2.pk, name='AC/DC', field='band_alias__alias'), expected)
    
#    def test_do_lookup(self):
#        pass
        
    def test_search(self):
        # Assert that the strategy's values_dict is reset 
        strat = self.strat()
        strat.values_dict = {1:'invalid'}
        rslt = strat.search('rose')
        self.assertTrue(len(rslt)>1)
