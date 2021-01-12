from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import F, Value, FloatField

from DBentry import models as _models
from DBentry.factory import make
from DBentry.tests.base import DataTestCase

# Stuff to test for:
#   - unaccent
#   - search rank (was: exact, startsw, contains)
#       for autocomplete
#           !! might be faster to just do it like it is now: order the results after the query
#           favoring slower queries over more in memory work has proven to be slower for the server
#   - use/inclusion of search fields
#   - words in search term being used individually (not a phrase search)
#       => 'Led Zeppelin' found by 'Zeppelin Led'
#   - can search for the beginning of a string (even with stop words)
#       => 'The Beatles' found by 'Th'
#   - should enable finding "Rock 'n' Roll" from "rock n roll"
#   - trigram support
#   - special cases: umlaute, ß, quotation marks and nickname markers: ",',(,),',"
#   - multiple words connected by AND? (doesn't the autocomplete partial match with OR??)
#   - languages (for both: SearchVectorField and SearchQuery)


# Other:
# TODO: SearchQuery with 'websearch' search_type argument: search like on google, etc.
#       - requires Django 3.1 (which requires Python > 3.5)
#       - requires Postgres 11 (Debian 11 Bullseye or install manually)
# NOTE: Ranking requires consulting the tsvector of each match: -> add a SearchVectorField column

class TestSearch(DataTestCase):

    model = _models.Band
    raw_data = [
        {
            'band_name': 'Hélène',
            'beschreibung': 'beschreibung',
            'bemerkungen': 'bemerkungen',
            'bandalias__alias': 'BandAlias'
        }
    ]

    def get_search_vector(self, search_fields=None):
        if search_fields is None:
            search_fields = [
                'band_name', 'beschreibung', 'bemerkungen', 'bandalias__alias']
        return SearchVector(*search_fields)

    def search(self, q, qs=None):
        if qs is None:
            qs = self.queryset
        if isinstance(q, str):
            q = SearchQuery(q)
        rank = SearchRank(F('search'), q)
        return qs.annotate(rank=rank).filter(search=q).order_by('-rank', 'band_name')

    def test_unaccent(self):
        # Assert that search uses unaccent.
        # Hélène <- Helene
        self.assertTrue(self.search('Helene'))
        self.obj1.band_name = 'Helene'
        self.obj1.save()
        self.assertTrue(self.search('Hélène'))

    def test_search_fields(self):
        # Assert that the search fields are queried.
        test_data = [
            # search_field, search term
            ('band_name', 'Hélène'),
            ('beschreibung', 'beschreibung'),
            ('bemerkungen', 'bemerkungen'),
            ('bandalias__alias', 'BandAlias')
        ]
        for search_field, search_term in test_data:
            with self.subTest(search_field=search_field, search_term=search_term):
                results = self.search(search_term)
                self.assertTrue(results)
                self.assertIn(self.obj1, results)

    def test_search_unordered(self):
        # Assert that words in the search term are used independently of each other (???)
        # 'Plant Robert' finds 'Robert Plant'
        obj = make(self.model, band_name='Led Zeppelin')
        results = self.search('Zeppelin Led', qs=obj.qs())
        self.assertTrue(results)
        self.assertIn(obj, results)

    def test_search_stop_word(self):
        # Assert a search term that is a stop word can still be used to find
        # matches.
        obj = make(self.model, band_name='The Beatles')
        results = self.search('The', qs=obj.qs())
        self.assertTrue(results)
        self.assertIn(obj, results)

    def test_rock_n_roll(self):
        # "Rock 'n' Roll" can be found with "rock n roll"
        # NOTE: what _exactly_ does this test?
        obj = make(self.model, band_name="Rock 'n' Roll")
        results = self.search("rock n roll", qs=obj.qs())
        self.assertTrue(results)
        self.assertIn(obj, results)

    def test_trigram(self):
        obj = make(self.model, band_name='Katy Stevens')
        results = self.search('Katie Stephens', qs=obj.qs())
        self.assertTrue(results)
        self.assertIn(obj, results)

    def test_partial_match(self):
        obj = make(self.model, band_name='Soundgarden')
        query = SearchQuery('Sound:*', search_type='raw')
        results=self.search(query, qs=obj.qs())
        self.assertTrue(results)
        self.assertIn(obj, results)

    def test_exact(self):
        # Assert that exact matches come first:
        make(self.model, band_name='Soundgarden')
        make(self.model, band_name='Garden Sound')
        make(self.model, band_name='Led Zeppelin')
        exact = make(self.model, band_name='Sound')
        queryset = self.model.objects
        results_exact = (
            queryset.filter(band_name='Sound')
            .annotate(rank=Value(value=1, output_field=FloatField()))
        )
        results_fts = self.search(
            SearchQuery('Sound:*', search_type='raw'),
            qs=queryset.exclude(id__in=results_exact.values_list('id', flat=True))
        )
        results = results_exact.union(results_fts).order_by('-rank', 'band_name')
        self.assertIn(exact, results)
        self.assertEqual(results[0], exact)

import time
from unittest import skip
@skip("Nah")
class TestBenchmark(DataTestCase):

    model = _models.Band

    @classmethod
    def setUpTestData(cls):
        cls.test_data = [make(cls.model, band_name='Led Zeppelin')]
        for i in range(10000):
            make(cls.model)
        super().setUpTestData()

    def print_times(self, times, desc):
        template = '\n{desc}\navg:\t{avg!r:.6}\tmin:\t{min!r:.6}\tmax:\t{max!r:.6}'
        format_kwargs = {
            'desc': desc,
            'avg': sum(times)/len(times),
            'min': min(times),
            'max': max(times)
        }
        print(template.format(**format_kwargs))

    def test_fts(self):
        times = []
        for i in range(100):
            start = time.perf_counter()
            qs = self.model.objects.filter(search=SearchQuery('Led:*', search_type='raw'))
            self.assertIn(self.obj1, qs)
            times.append(time.perf_counter() - start)
        self.print_times(times, 'FTS')

    def test_find(self):
        times = []
        for i in range(100):
            start = time.perf_counter()
            qs = self.model.objects.find('Led')
            self.assertIn((self.obj1.pk, 'Led Zeppelin'), qs)
            times.append(time.perf_counter() - start)
        self.print_times(times, 'FIND')
