from django.utils.translation import override as translation_override

import DBentry.models as _models
from DBentry.factory import make
from DBentry.query import (
    BaseSearchQuery, NameFieldSearchQuery, PrimaryFieldsSearchQuery,
    ValuesDictSearchQuery
)
from DBentry.tests.base import DataTestCase


class QueryTestCase(DataTestCase):

    model = _models.band
    query_class = None

    @classmethod
    def setUpTestData(cls):
        cls.axl = make(_models.musiker,
            kuenstler_name='Axl Rose', musiker_alias__alias='Axel Rose')

        cls.obj1 = make(cls.model,
            band_name="Guns 'N Roses", band_alias__alias='Guns and Roses',
            musiker=cls.axl)
        # obj2 can only be found via 'Axl' when searching 'Rose'
        cls.obj2 = make(cls.model,
            band_name="AC/DC", band_alias__alias='ACDC', musiker=cls.axl)
        # obj3 is meant to never be found
        cls.obj3 = make(cls.model, band_name="Rolling Stones")
        # obj4 start with 'Rose'
        cls.obj4 = make(cls.model, band_name="Rosewood")
        # obj5 contains 'Rose'
        cls.obj5 = make(cls.model, band_name='More Roses')
        # obj6's alias icontains 'Rose'
        cls.obj6 = make(cls.model, band_name='Beep', band_alias__alias='Booproses')

        cls.test_data = [
            cls.obj1, cls.obj2, cls.obj3, cls.obj4, cls.obj5, cls.obj6, cls.axl]

        super().setUpTestData()

    def make_query(self, **kwargs):
        if 'queryset' not in kwargs:
            kwargs['queryset'] = self.queryset
        return self.query_class(**kwargs)

    def append_suffix(self, query, objs, search_field, lookup):
        # Helper method that appends suffixes to the objects in objs.
        suffix = query.get_suffix(search_field, lookup)
        result = []
        for obj in objs:
            result.append(
                query.create_result_item(obj, suffix)
            )
        return result


class TestBaseQuery(QueryTestCase):

    query_class = BaseSearchQuery

    def test_get_suffix(self):
        # Assert that the correct suffix for a given search_field is returned.
        suffixes = {
            'beschreibung': 'Beschreibung',
            'beschreibung__icontains': 'In Beschreibung'
        }
        query = self.make_query(suffixes=suffixes)
        # search_field + lookup in suffixes
        self.assertEqual(
            query.get_suffix('beschreibung', '__icontains'), 'In Beschreibung')
        query.suffixes.pop('beschreibung__icontains')
        # search_field is in suffixes
        self.assertEqual(
            query.get_suffix('beschreibung', '__icontains'), 'Beschreibung')
        query.suffixes.pop('beschreibung')
        # no suffix found
        self.assertEqual(
            query.get_suffix('beschreibung', '__icontains'), '')

    def test_append_suffix(self):
        # Assert that a suffix for a given search_field is appended.
        self.assertEqual(
            self.make_query().append_suffix('AC/DC', 'Band-Alias'),
            "AC/DC (Band-Alias)"
        )

    def test_append_suffix_no_suffix(self):
        # Assert that no suffix is appended if use_suffix is False or if
        # given suffix is an empty string.
        use_suffix_msg = "No suffix should be appended if 'use_suffix' is False."
        empty_suffix_msg = "No suffix should be appended if the suffix is an empty string."
        test_data = [
            # (use_suffix, suffix, msg)
            (False, 'Beep', use_suffix_msg),
            (True, '', empty_suffix_msg)
        ]
        for use_suffix, suffix, msg in test_data:
            query = self.make_query(use_suffix=use_suffix)
            with self.subTest(use_suffix=use_suffix, suffix=suffix):
                self.assertEqual(
                    query.append_suffix('AC/DC', suffix), 'AC/DC', msg=msg)

    def test_do_lookup(self):
        q = 'Axel Rose'
        lookup = '__icontains'
        search_field = 'musiker__musiker_alias__alias'
        expected = [(self.obj1.pk, "Guns 'N Roses (Mitglied-Alias)"), (self.obj2.pk, "AC/DC (Mitglied-Alias)")]
        query = self.make_query()
        self.assertListEqualSorted(query._do_lookup(lookup, search_field, q), expected)
        self.assertListEqualSorted(list(query.ids_found), [self.obj1.pk, self.obj2.pk])

    def test_date_lookup(self):
        a1 = make(_models.ausgabe, e_datum='1986-08-15')
        a2 = make(_models.ausgabe, e_datum='1986-08-18')
        a3 = make(_models.ausgabe, e_datum='1986-09-18')
        test_data = [
            ('__iexact', '1986-08-15', [a1.pk]),
            ('__iexact', '15.08.1986', [a1.pk]),
            ('__istartswith', '1986-08', [a1.pk, a2.pk]),
            ('__istartswith', '08.1986', [a1.pk, a2.pk]),
            ('__istartswith', '1986', [a1.pk, a2.pk, a3.pk]),
            ('__icontains', '1986-08', [a1.pk, a2.pk]),
            ('__icontains', '08.1986', [a1.pk, a2.pk]),
            ('__icontains', '1986', [a1.pk, a2.pk, a3.pk]),
        ]
        for lookup, q, expected in test_data:
            query = self.make_query(queryset = _models.ausgabe.objects)
            q = query.clean_q(q, 'e_datum')
            results = query._do_lookup(lookup, 'e_datum', q)
            with self.subTest(lookup=lookup, q=q):
                self.assertEqual(
                    sorted([i[0] for i in results]),
                    sorted(expected)
                )

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

        rose_band = _models.band.objects.create(band_name='Rose')
        some_other_band = make(_models.band, band_name='Boop', musiker__kuenstler_name = 'Rose')

        yet_another_band = make(_models.band, band_name='NoName', musiker__kuenstler_name='Roseman')

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

    def append_suffix(self, query, objs, search_field, lookup):
        # NameFieldSearchQuery uses two-tuples, not model instances.
        # For ease of use, however, model instances are usually passed to this
        # method.
        new_objs = []
        for obj in objs:
            if isinstance(obj, self.model):
                new_objs.append((obj.pk, getattr(obj, query.name_field)))
            else:
                new_objs.append(obj)
        return super().append_suffix(query, new_objs, search_field, lookup)

    def test_init(self):
        # Set name_field from primary_search_fields or seconary_search_fields
        self.assertEqual(self.make_query(name_field = '').name_field, 'band_name')
        self.assertEqual(self.make_query(primary_search_fields=[]).name_field, 'band_name')


class TestValuesDictQuery(TestNameFieldQuery):

    query_class = ValuesDictSearchQuery

    def make_query(self, values_dict = None, **kwargs):
        query = super().make_query(**kwargs)
        query.values_dict = values_dict
        if values_dict is None:
            if 'queryset' in kwargs:
                query.values_dict = kwargs['queryset'].values_dict(*query.search_fields)
            else:
                query.values_dict = self.queryset.values_dict(*query.search_fields) 
        return query

    def append_suffix(self, query, objs, search_field, lookup):
        # ValuesDictSearchQuery uses values_dict(), not model instances.
        # For ease of use, however, model instances are usually passed to this
        # method.
        new_objs = []
        for obj in objs:
            if isinstance(obj, self.model):
                # 2-tuple of (pk, values of values_dict) expected
                new_objs.append((
                    obj.pk,
                    obj.qs().values_dict(*query.search_fields).pop(obj.pk)
                ))
            else:
                new_objs.append(obj)
        return super().append_suffix(query, new_objs, search_field, lookup)

    def test_get_values_for_result(self):
        # Assert that the correct values are returned for a given 'result' object.
        query = self.make_query()
        self.assertEqual(
            query.get_values_for_result((1, {query.name_field: ('Beep', )})),
            (1, 'Beep')
        )

    def test_get_queryset(self):
        # ValuesDictSearchQuery.get_queryset filters the _root_queryset to limit the amount of records
        # fetched by values_dict()
        expected = list(self.queryset.exclude(band_name='Rolling Stones').values_list('pk', flat=True))
        self.assertQSValuesList(self.make_query().get_queryset(q = 'Rose'), 'pk', expected)

    def test_partial_match(self):
        # Assert that search can find 'More Roses' via search term 'Roses More'.
        # Add two more instances to verify that ALL search terms must be in a
        # result.
        make(self.model, band_name='Roses')
        make(self.model, band_name='More')
        search_results = self.make_query(
            queryset=self.model.objects.all()).search('Roses More')
        self.assertEqual(search_results, ([(self.obj5.pk, 'More Roses')], True))

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

        rose_band = _models.band.objects.create(band_name='Rose')
        some_other_band = make(_models.band, band_name='Boop', musiker__kuenstler_name = 'Rose')

        yet_another_band = make(_models.band, band_name='NoName', musiker__kuenstler_name='Roseman')

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
        expected = self.append_suffix(query, [self.obj4, self.obj1, self.obj5], search_field, lookup)
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
