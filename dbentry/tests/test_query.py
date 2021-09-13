from django.utils.translation import override as translation_override

import dbentry.models as _models
from dbentry.factory import make
from dbentry.query import (
    BaseSearchQuery, NameFieldSearchQuery, PrimaryFieldsSearchQuery,
    ValuesDictSearchQuery
)
from dbentry.tests.base import DataTestCase


# noinspection SpellCheckingInspection
class QueryTestCase(DataTestCase):

    model = _models.Band
    query_class = None

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(
            cls.model, band_name="Guns 'N Roses", bandalias__alias='Guns and Roses')
        # obj2 beschreibung starts with 'Roses'.
        cls.obj2 = make(
            cls.model, band_name="AC/DC", bandalias__alias='ACDC',
            beschreibung='Roses are red.'
        )
        # obj3 is meant to never be found
        cls.obj3 = make(cls.model, band_name="Rolling Stones")
        # obj4 start with 'Rose'
        cls.obj4 = make(cls.model, band_name="Rosewood")
        # obj5 contains 'Rose'
        cls.obj5 = make(cls.model, band_name='More Roses')
        # obj6's alias icontains 'Rose'
        cls.obj6 = make(cls.model, band_name='Beep', bandalias__alias='Booproses')

        cls.test_data = [
            cls.obj1, cls.obj2, cls.obj3, cls.obj4, cls.obj5, cls.obj6]

        super().setUpTestData()

    def make_query(self, **kwargs):
        if 'queryset' not in kwargs:
            kwargs['queryset'] = self.queryset
        if 'suffixes' not in kwargs:
            kwargs['suffixes'] = {
                'bandalias__alias': 'Alias',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        return self.query_class(**kwargs)


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
        q = 'Boop'
        lookup = '__icontains'
        search_field = 'bandalias__alias'
        expected = [(self.obj6.pk, "Beep (Alias)")]
        query = self.make_query()
        self.assertEqual(query._do_lookup(lookup, search_field, q), expected)
        self.assertIn(self.obj6.pk, query.ids_found)
        self.assertEqual(len(query.ids_found), 1)

    def test_date_lookup(self):
        a1 = make(_models.Ausgabe, e_datum='1986-08-15')
        a2 = make(_models.Ausgabe, e_datum='1986-08-18')
        a3 = make(_models.Ausgabe, e_datum='1986-09-18')
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
            query = self.make_query(
                queryset=_models.Ausgabe.objects, search_fields=['_name', 'e_datum'])
            q = query.clean_q(q, 'e_datum')
            results = query._do_lookup(lookup, 'e_datum', q)
            with self.subTest(lookup=lookup, q=q):
                self.assertEqual(
                    sorted(i[0] for i in results),
                    sorted(expected)
                )

    def test_exact_search(self):
        # lookup = '__iexact'

        q = 'AC/DC'
        query = self.make_query()
        self.assertFalse(query.exact_search('bandalias__alias', q))
        self.assertFalse(query.exact_match)

        q = 'AC/DC'
        query = self.make_query()
        search_field = 'band_name'
        self.assertEqual(query.exact_search(search_field, q), [(self.obj2.pk, "AC/DC")])
        self.assertTrue(query.exact_match)

        q = 'ACDC'
        query = self.make_query()
        search_field = 'bandalias__alias'
        self.assertEqual(query.exact_search(search_field, q), [(self.obj2.pk, "AC/DC (Alias)")])
        self.assertTrue(query.exact_match)

    def test_startsw_search(self):
        # lookup = '__istartswith'

        q = 'AC/DCS'
        self.assertFalse(self.make_query().startsw_search('band_name', q))

        q = 'AC/'
        query = self.make_query()
        search_field = 'band_name'
        self.assertEqual(query.startsw_search(search_field, q), [(self.obj2.pk, "AC/DC")])

        q = 'ACD'
        query = self.make_query()
        search_field = 'bandalias__alias'
        self.assertEqual(query.startsw_search(search_field, q), [(self.obj2.pk, "AC/DC (Alias)")])

    def test_contains_search(self):
        # lookup = '__icontains'

        q = 'AC/DCS'
        self.assertFalse(self.make_query().contains_search('band_name', q))

        q = 'C/D'
        query = self.make_query()
        search_field = 'band_name'
        self.assertEqual(query.contains_search(search_field, q), [(self.obj2.pk, "AC/DC")])

        q = 'CD'
        query = self.make_query()
        search_field = 'bandalias__alias'
        self.assertEqual(query.contains_search(search_field, q), [(self.obj2.pk, "AC/DC (Alias)")])

    def test_search(self):
        def extract_ids(results):
            ids = []
            for result in results:
                if isinstance(result, tuple):
                    ids.append(result[0])
                else:
                    ids.append(result.pk)
            return sorted(ids)

        q = 'Rose'
        search_results, exact_match = self.make_query().search(q)
        expected = list(
            self.queryset
            .exclude(pk__in=[self.obj3.pk])
            .order_by('pk')
            .values_list('pk', flat=True)
        )
        self.assertEqual(extract_ids(search_results), expected)
        self.assertFalse(exact_match)

        q = 'Roses'
        search_results, exact_match = self.make_query().search(q)
        expected = [self.obj1.pk, self.obj2.pk, self.obj5.pk, self.obj6.pk]
        self.assertEqual(extract_ids(search_results), expected)
        self.assertFalse(exact_match)

        q = 'AC/DC'
        search_results, exact_match = self.make_query().search(q)
        expected = [self.obj2.pk]
        self.assertEqual(extract_ids(search_results), expected)
        self.assertTrue(exact_match)

    def test_search_returns_qs_on_no_q(self):
        # Assert that search returns the root queryset when q is 'False'.
        query = self.make_query()
        query._root_queryset = "This isn't a queryset!"
        search_results, _exact_match = query.search(q=None)
        self.assertEqual(search_results, "This isn't a queryset!")

    def test_num_queries(self):
        # len(self.model.get_search_fields()) * (iexact,istartswith,icontains)
        q = 'Rose'
        query = self.make_query()
        with self.assertNumQueries(len(self.model.get_search_fields()) * 3):
            query.search(q)

    def test_reorder_results(self):
        # Assert that the order of the results matches the order of the
        # initial queryset. NO SEPARATOR.
        qs_order = list(
            self.queryset
            .exclude(pk__in=[self.obj3.pk])
            .values_list('pk', flat=True)
        )
        query = self.make_query(use_separator=False)
        ordered_results, _ = query.search('Rose', ordered=True)
        self.assertEqual(
            qs_order, [tpl[0] for tpl in ordered_results]
        )


# noinspection SpellCheckingInspection
class TestPrimaryFieldsQuery(TestBaseQuery):

    query_class = PrimaryFieldsSearchQuery

    @translation_override(language=None)
    def test_get_separator(self):
        q = 'Test'
        sep = self.make_query().create_separator_item(q)
        self.assertEqual(sep, (0, '------- weak hits for "Test" -------'))

        # with separator_text argument
        separator_text = 'Beep boop "{q}"'
        sep = self.make_query().create_separator_item(q, separator_text)
        self.assertEqual(sep, (0, '--------- Beep boop "Test" ---------'))

    def test_exact_search(self):
        # exact_match should stay False if exact_matches for secondary search
        # fields were found.
        q = 'Rosewood'
        query = self.make_query()
        search_field = 'band_name'
        query.exact_search(search_field, q)
        self.assertTrue(query.exact_match)

        q = 'ACDC'
        query = self.make_query()
        search_field = 'bandalias__alias'
        query.exact_search(search_field, q)
        self.assertFalse(query.exact_match)

    def test_search(self):
        # obj1 = "Guns 'N Roses"
        # obj2 = 'AC/DC'
        # obj3 = 'Rolling Stones'
        # obj4 = 'Rosewood'
        # obj5 = 'More Roses'
        # obj6 = 'Beep', alias = 'Booproses'
        # Check that the results are ordered according to the _search query
        rose_band = _models.Band.objects.create(band_name='Rose')
        some_other_band = make(
            _models.Band, band_name='Boop', bandalias__alias='Rose')
        yet_another_band = make(
            _models.Band, band_name='NoName', bandalias__alias='Roseman')

        q = 'Rose'
        query = self.make_query()
        search_results, exact_match = query.search(q)

        self.assertEqual(len(search_results), 9)

        # Exact primary field match first
        self.assertEqual(search_results[0], (rose_band.pk, "Rose"))

        # Primary startsw matches next
        self.assertEqual(search_results[1], (self.obj4.pk, "Rosewood"))

        # Then primary contains matches
        expected = [
            (self.obj1.pk, "Guns 'N Roses"),
            (self.obj5.pk, "More Roses")
        ]
        self.assertEqual(search_results[2:4], expected)

        # Then secondary exact_matches
        self.assertEqual(search_results[4], (some_other_band.pk, "Boop (Alias)"))

        # weak hits --- a separator followed by secondary startsw and contains matches
        self.assertEqual(search_results[5], (0, '--- schwache Treffer für "Rose" ----'))

        # Then secondary startsw matches
        self.assertEqual(search_results[6], (yet_another_band.pk, "NoName (Alias)"))

        # Finally, secondary contains matches
        self.assertEqual(search_results[7], (self.obj6.pk, "Beep (Alias)"))
        self.assertEqual(search_results[8], (self.obj2.pk, "AC/DC (Beschreibung)"))

    def test_reorder_results_with_separator(self):
        # Assert that the order of the results matches the order of the
        # initial queryset. WITH SEPARATOR.
        strong_qs = (
            self.queryset
            .filter(pk__in=[self.obj1.pk, self.obj4.pk, self.obj5.pk])
            .values_list('pk', flat=True)
        )
        weak_qs = (
            self.queryset
            .filter(pk__in=[self.obj2.pk, self.obj6.pk])
            .values_list('pk', flat=True)
        )
        query = self.make_query(use_separator=True)
        # Need to know where the query would put the separator for an unordered
        # result. Reordering results must only reorder strong results with other
        # strong results (same for weak results), meaning the index of the
        # separator must be preserved.
        unordered_results, _ = query.search('Rose', ordered=False)
        result_ids = [tpl[0] for tpl in unordered_results]
        separator_id = query.create_separator_item('')[0]
        self.assertIn(separator_id,  result_ids, msg='Separator expected.')
        sep_index = result_ids.index(separator_id)
        # Now get the ordered results.
        ordered_results, _ = query.search('Rose', ordered=True)
        result_ids = [tpl[0] for tpl in ordered_results]
        self.assertIn(separator_id,  result_ids, msg='Separator expected.')
        self.assertEqual(
            result_ids.index(separator_id), sep_index,
            msg='Separator index must be preserved.')
        strong, weak = result_ids[:sep_index], result_ids[sep_index + 1:]
        self.assertEqual(list(strong_qs), strong)
        self.assertEqual(list(weak_qs), weak)


class TestNameFieldQuery(TestPrimaryFieldsQuery):

    query_class = NameFieldSearchQuery

    def test_init(self):
        # Set name_field from primary_search_fields or secondary_search_fields
        self.assertEqual(self.make_query(name_field='').name_field, 'band_name')
        self.assertEqual(self.make_query(primary_search_fields=[]).name_field, 'band_name')


# noinspection SpellCheckingInspection
class TestValuesDictQuery(TestNameFieldQuery):

    query_class = ValuesDictSearchQuery

    def make_query(self, values_dict=None, **kwargs):
        query = super().make_query(**kwargs)
        query.values_dict = values_dict
        if values_dict is None:
            if 'queryset' in kwargs:
                query.values_dict = kwargs['queryset'].values_dict(*query.search_fields)
            else:
                query.values_dict = self.queryset.values_dict(*query.search_fields)
        return query

    def test_get_queryset(self):
        # Assert that ValuesDictSearchQuery.get_queryset applies a
        # '__icontains=q' filter to the root queryset to limit the amount of
        # records fetched by values_dict().
        queryset = self.make_query().get_queryset(q='Rose')
        # "Rolling Stones" should never be found and thus should not be included
        # in the root queryset.
        self.assertFalse(queryset.filter(band_name="Rolling Stones").exists())

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
        # Compared to PrimaryFieldsSearchQuery, the order changes a little as
        # we are able to split up the search term and look for bits of it in
        # the search_fields.
        rose_band = _models.Band.objects.create(band_name='Rose')
        some_other_band = make(
            _models.Band, band_name='Boop', bandalias__alias='Rose')
        yet_another_band = make(
            _models.Band, band_name='NoName', bandalias__alias='Roseman')
        should_have_setup_this_better = make(
            _models.Band, band_name="SomethingContainingRoses")

        q = 'Rose'
        query = self.make_query()
        search_results, exact_match = query.search(q)

        self.assertEqual(len(search_results), 10)

        # Exact primary field match first
        self.assertEqual(search_results[0], (rose_band.pk, 'Rose'))

        # No partial primary exact found

        # Then startsw matches + partial startsw matches
        # (which are weighted equally and ordered)
        # => 'Rosewood', "Guns N' Roses", 'More Roses'
        expected = [
            (self.obj4.pk, "Rosewood"),
            (self.obj1.pk, "Guns 'N Roses"),
            (self.obj5.pk, "More Roses")
        ]
        self.assertEqual(search_results[1:4], expected)

        # Then primary contains matches
        self.assertEqual(
            search_results[4],
            (should_have_setup_this_better.pk, "SomethingContainingRoses")
        )

        # Then secondary exact_matches
        self.assertEqual(search_results[5], (some_other_band.pk, "Boop (Alias)"))

        # weak hits --- a separator followed by secondary startsw and contains matches
        self.assertEqual(search_results[6], (0, '--- schwache Treffer für "Rose" ----'))

        # Then secondary startsw matches
        self.assertEqual(search_results[7], (yet_another_band.pk, "NoName (Alias)"))

        # Finally, secondary contains matches
        self.assertEqual(search_results[8], (self.obj6.pk, "Beep (Alias)"))
        self.assertEqual(search_results[9], (self.obj2.pk, "AC/DC (Beschreibung)"))

    def test_search_resets_values_dict(self):
        # Assert that the strategy's values_dict is reset
        query = self.make_query()
        query.values_dict = {1: 'invalid'}
        result = query.search('rose')
        self.assertTrue(len(result) > 1)

    def test_num_queries(self):
        q = 'Rose'
        query = self.make_query(use_separator=False)
        with self.assertNumQueries(1):
            query.search(q)

    def test_contains_search(self):
        # lookup = '__icontains'

        q = 'AC/DCS'
        self.assertFalse(self.make_query().contains_search('band_name', q))

        q = 'C/D'
        query = self.make_query()
        search_field = 'band_name'
        self.assertEqual(query.contains_search(search_field, q), [(self.obj2.pk, "AC/DC")])

        q = 'CD'
        query = self.make_query()
        search_field = 'bandalias__alias'
        # expected = self.append_suffix(query, [self.obj2], search_field, lookup)
        self.assertEqual(query.contains_search(search_field, q), [(self.obj2.pk, "AC/DC (Alias)")])