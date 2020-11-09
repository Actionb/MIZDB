from django.contrib.postgres.search import SearchVector

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
#        return qs.find(q)
        return qs.annotate(search=self.get_search_vector()).filter(search=q)

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

    def test_rank(self):
        # Assert that the results are ranked according to:
        # exact matches -> startswith matches -> contains matches
        contains = make(self.model, band_name='Thesoundstuff')
        exact = make(self.model, band_name='Sound')
        startswith = make(self.model, band_name='Soundgarden')
        results = self.search(
            'Sound',
            qs=self.model.objects.filter(id__in=[contains.pk, exact.pk, startswith.pk])
        )
        self.assertEqual(results.count(), 3)
#        self.assertIn(exact, results)
#        self.assertIn(startswith, results)
#        self.assertIn(contains, results)
        self.assertEqual(list(results), [exact, startswith, contains])
