from .base import *

from DBentry.query import *

class QueryTestCase(DataTestCase):
    
    model = band
    query_class = None
    
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
        
    def make_query(self, **kwargs):
        if 'queryset' not in kwargs:
            kwargs['queryset'] = self.queryset
        return self.query_class(**kwargs)
        
    def append_suffix(self, query, obj, search_field, lookup):
        return query.append_suffix(obj, search_field, lookup)

class TestBaseQuery(QueryTestCase):
    
    query_class = BaseSearchQuery
        
    def test_get_suffix(self):
        query = self.make_query()
        self.assertEqual(query.get_suffix('musiker__musiker_alias__alias'), 'Mitglied-Alias')
        new_suffix = query.suffix.copy()
        new_suffix['band_name__icontains'] = 'Tested!'
        self.assertEqual(self.make_query(suffix=new_suffix).get_suffix('band_name', '__icontains'), 'Tested!')
        
    def test_append_suffix(self):
        expected = [(self.obj2.pk,"AC/DC (Band-Alias)")]
        self.assertEqual(self.make_query().append_suffix([self.obj2], 'band_alias__alias'), expected)
        self.assertEqual(self.make_query().append_suffix([self.obj2], 'not_in_suffixes'), [(self.obj2.pk, 'AC/DC')])
        
    def test_do_lookup(self):
        q = 'Axel Rose'
        lookup = '__icontains'
        search_field = 'musiker__musiker_alias__alias'
        expected = [(self.obj1.pk, "Guns 'N Roses (Mitglied-Alias)"), (self.obj2.pk, "AC/DC (Mitglied-Alias)")]
        query = self.make_query()
        self.assertListEqualSorted(query._do_lookup(lookup, search_field, q), expected)
        self.assertListEqualSorted(list(query.ids_found), [self.obj1.pk, self.obj2.pk])
        
    def test_exact_search(self):
        lookup = '__iexact'
        
        q = 'AC/DC'
        expected = []
        query = self.make_query()
        self.assertListEqualSorted(query.exact_search('band_alias__alias', q), expected)
        self.assertFalse(query.exact_match)
        
        q = 'AC/DC'
        query = self.make_query()
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.exact_search(search_field, q), expected)
        self.assertTrue(query.exact_match)
        
        q = 'ACDC'
        query = self.make_query()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.exact_search(search_field, q), expected)
        self.assertTrue(query.exact_match)
        
        q = 'Axl Rose'
        query = self.make_query()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.exact_search(search_field, q), expected)
        self.assertTrue(query.exact_match)
        
        q = 'Axel Rose'
        query = self.make_query()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.exact_search(search_field, q), expected)
        self.assertTrue(query.exact_match)
        
    def test_startsw_search(self):
        lookup = '__istartswith'
        
        q = 'AC/DCS'
        expected = []
        self.assertListEqualSorted(self.make_query().startsw_search('band_name', q), expected)
        
        q = 'AC/'
        query = self.make_query()
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.startsw_search(search_field, q), expected, msg="query: {}".format(query))
        
        q = 'ACD'
        query = self.make_query()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.startsw_search(search_field, q), expected)
        
        q = 'Axl'
        query = self.make_query()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.startsw_search(search_field, q), expected)
        
        q = 'Axel'
        query = self.make_query()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.startsw_search(search_field, q), expected)
        
    def test_contains_search(self):
        lookup = '__icontains'
        
        q = 'AC/DCS'
        expected = []
        self.assertListEqualSorted(self.make_query().contains_search('band_name', q), expected)
        
        q = 'C/D'
        query = self.make_query()
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.contains_search(search_field, q), expected)
        
        #['band_name', 'band_alias__alias', 'musiker__kuenstler_name', 'musiker__musiker_alias__alias']
        q = 'CD'
        query = self.make_query()
        search_field = 'band_alias__alias'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.contains_search(search_field, q), expected)
        
        q = 'xl R'
        query = self.make_query()
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.contains_search(search_field, q), expected)
        
        q = 'xel R'
        query = self.make_query()
        search_field = 'musiker__musiker_alias__alias'
        expected = self.append_suffix(query, [self.obj1, self.obj2], search_field, lookup)
        self.assertListEqualSorted(query.contains_search(search_field, q), expected)
        
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
        search_results, exact_match = self.make_query().search(q)
        expected = list(self.queryset.exclude(band_name='Rolling Stones').values_list('pk', flat=True))
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertFalse(exact_match)
        
        q = 'Roses'
        search_results, exact_match = self.make_query().search(q)
        expected = [self.obj1.pk, self.obj5.pk, self.obj6.pk]
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertFalse(exact_match)
        
        q = 'AC/DC'
        search_results, exact_match = self.make_query().search(q)
        expected = [self.obj2.pk]
        self.assertListEqualSorted(extract_ids(search_results), expected)
        self.assertTrue(exact_match)
        
    def test_search_returns_qs_on_no_q(self):
        search_results, exact_match = self.make_query().search(q=None)
        expected = list(self.queryset.values_list('pk', flat=True))
        self.assertQSValuesList(search_results, 'pk', expected)
            
    def test_num_queries(self):
        # len(self.model.get_search_fields()) * (iexact,istartswith,icontains)
        q = 'Rose'
        query = self.make_query()
        with self.assertNumQueries(len(self.model.get_search_fields())*3):
            query.search(q)
        
        
class TestPrimaryFieldsQuery(TestBaseQuery):
    
    query_class = PrimaryFieldsSearchQuery
        
    @translation_override(language = None)
    def test_get_separator(self):
        q = 'Test'
        sep = self.make_query().get_separator(q)
        self.assertEqual(sep, '------- weak hits for "Test" -------')
        
        # with separator_text argument
        separator_text = 'Beep boop "{q}"'
        sep = self.make_query().get_separator(q, separator_text)
        self.assertEqual(sep, '--------- Beep boop "Test" ---------')
        
    def test_exact_search(self):
        # exact_match should stay False if exact_matches for secondary search fields were found
        q = 'Axl'
        query = self.make_query()
        search_field = 'musiker__kuenstler_name'
        query.exact_search(search_field, q)
        self.assertFalse(query.exact_match)
        
        q = 'ACDC'
        query = self.make_query()
        search_field = 'band_alias__alias'
        query.exact_search(search_field, q)
        self.assertTrue(query.exact_match)
        
    def test_search(self):
        # obj1 = "Guns 'N Roses"
        # obj2 = 'AC/DC'
        # obj3 = 'Rolling Stones'
        # obj4 = 'Rosewood'
        # obj5 = 'More Roses'
        # obj6 = 'Beep', alias = 'Booproses'
        # Check that the results are ordered according to the _search query
        
        rose_band = band.objects.create(band_name='Rose')
        some_other_band = band.objects.create(band_name='Boop')
        rose_musiker = musiker.objects.create(kuenstler_name='Rose')
        m2m_band_musiker.objects.create(musiker=rose_musiker, band=some_other_band)
        
        yet_another_band = band.objects.create(band_name='NoName')
        rose_musiker2 = musiker.objects.create(kuenstler_name='Roseman')
        m2m_band_musiker.objects.create(musiker=rose_musiker2, band=yet_another_band)
        
        q = 'Rose'
        query= self.make_query()
        search_results, exact_match = query.search(q)
        
        self.assertEqual(len(search_results), 9)
        
        # Exact primary field match first
        lookup = '__iexact'
        search_field = 'band_name'
        expected = self.append_suffix(query, [rose_band], search_field, lookup)
        self.assertEqual([search_results[0]], expected)
        
        # Primary startsw matches next
        lookup = '__istartswith'
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj4], search_field, lookup)
        self.assertEqual([search_results[1]], expected)
        
        # Then primary contains matches
        lookup = '__icontains'
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj1, self.obj5], search_field, lookup)
        self.assertEqual(search_results[2:4], expected)
        
        lookup = '__istartswith'
        search_field = 'band_alias__alias'
        expected = self.append_suffix(query, [self.obj6], search_field, lookup)
        self.assertEqual([search_results[4]], expected)
        
        # Then secondary exact_matches
        lookup = '__iexact'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [some_other_band], search_field, lookup)
        self.assertEqual([search_results[5]], expected)
        
        # weak hits --- a separator followed by secondary startsw and contains matches
        self.assertEqual(search_results[6], (0, query.get_separator(q)))
        
        # Then secondary startsw matches
        lookup = '__istartswith'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [yet_another_band], search_field, lookup)
        self.assertEqual([search_results[7]], expected)
        
        # Finally, secondary contains matches
        lookup = '__icontains'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertEqual([search_results[8]], expected)
        
        
class TestNameFieldQuery(TestPrimaryFieldsQuery):
    
    query_class = NameFieldSearchQuery
    
    def append_suffix(self, query, obj, search_field, lookup):
        tuple_list = [(o.pk, getattr(o, query.name_field)) for o in obj]
        return query.append_suffix(tuple_list, search_field, lookup)
        
    def test_init(self):
        # Set name_field from primary_search_fields or seconary_search_fields
        self.assertEqual(self.make_query(name_field = '').name_field, 'band_name')
        self.assertEqual(self.make_query(primary_search_fields=[]).name_field, 'band_name')
        
    def test_append_suffix(self):
        # expects a list of tuples --- tuple_list, field, lookup=''
        expected = [(self.obj2.pk, 'AC/DC (Band-Alias)')]
        self.assertEqual(self.make_query().append_suffix(tuple_list=[(self.obj2.pk, 'AC/DC')], field='band_alias__alias'), expected)

class TestValuesDictQuery(TestNameFieldQuery):
    
    query_class = ValuesDictSearchQuery
    
    def make_query(self, values_dict = None, **kwargs):
        query = super().make_query(**kwargs)
        query.values_dict = values_dict or self.queryset.values_dict(*query.search_fields) 
        return query
    
    def test_get_queryset(self):
        # ValuesDictSearchQuery.get_queryset filters the _root_queryset to limit the amount of records
        # fetched by values_dict()
        expected = list(self.queryset.exclude(band_name='Rolling Stones').values_list('pk', flat=True))
        self.assertQSValuesList(self.make_query().get_queryset(q = 'Rose'), 'pk', expected)
        
    def test_search(self):
        # obj1 = "Guns 'N Roses"
        # obj2 = 'AC/DC'
        # obj3 = 'Rolling Stones'
        # obj4 = 'Rosewood'
        # obj5 = 'More Roses'
        # obj6 = 'Beep', alias = 'Booproses'
        # Check that the results are ordered according to the _search query
        # Compared to PrimaryFieldsSearchQuery, the order changes a little as we are able to split up the search term and look 
        # for bits of it in the search_fields
        
        rose_band = band.objects.create(band_name='Rose')
        some_other_band = band.objects.create(band_name='Boop')
        rose_musiker = musiker.objects.create(kuenstler_name='Rose')
        m2m_band_musiker.objects.create(musiker=rose_musiker, band=some_other_band)
        
        yet_another_band = band.objects.create(band_name='NoName')
        rose_musiker2 = musiker.objects.create(kuenstler_name='Roseman')
        m2m_band_musiker.objects.create(musiker=rose_musiker2, band=yet_another_band)
        
        q = 'Rose'
        query= self.make_query()
        search_results, exact_match = query.search(q)
        
        self.assertEqual(len(search_results), 9)
        
        # Exact primary field match first
        lookup = '__iexact'
        search_field = 'band_name'
        expected = self.append_suffix(query, [rose_band], search_field, lookup)
        self.assertEqual([search_results[0]], expected)
        
        # No partial primary exact found
        
        # Then startsw matches + partial startsw matches (which are weighted equally and ordered)
        # "Guns N' Roses", 'More Roses', 'Rosewood'
        lookup = '__istartswith'
        search_field = 'band_name'
        expected = self.append_suffix(query, [self.obj1, self.obj5, self.obj4], search_field, lookup)
        self.assertEqual(search_results[1:4], expected)
        
        # Then primary contains matches
        # obj6: alias = 'Booproses'
        lookup = '__istartswith'
        search_field = 'band_alias__alias'
        expected = self.append_suffix(query, [self.obj6], search_field, lookup)
        self.assertEqual([search_results[4]], expected)
        
        # Then secondary exact_matches
        lookup = '__iexact'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [some_other_band], search_field, lookup)
        self.assertEqual([search_results[5]], expected)
        
        # weak hits --- a separator followed by secondary startsw and contains matches
        self.assertEqual(search_results[6], (0, query.get_separator(q)))
        
        # Then secondary startsw matches
        lookup = '__istartswith'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [yet_another_band], search_field, lookup)
        self.assertEqual([search_results[7]], expected)
        
        # Finally, secondary contains matches
        lookup = '__icontains'
        search_field = 'musiker__kuenstler_name'
        expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertEqual([search_results[8]], expected)
        
    def test_search_resets_values_dict(self):
        # Assert that the strategy's values_dict is reset 
        query = self.make_query()
        query.values_dict = {1:'invalid'}
        rslt = query.search('rose')
        self.assertTrue(len(rslt)>1)
            
    def test_num_queries(self):
        q = 'Rose'
        query = self.make_query(use_separator = False)
        with self.assertNumQueries(1):
            query.search(q)
        
