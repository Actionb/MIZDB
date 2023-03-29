import json
from unittest.mock import patch, Mock

from django.test import override_settings
from django.urls import path, reverse

from dbentry.site.views.search import SearchbarSearch
from tests.case import DataTestCase, ViewTestCase
from tests.model_factory import make
from .models import Band, Musician, Country, TextSearchQuery


def dummy_view(request, *args, **kwargs):
    return None


class URLConf:
    urlpatterns = [
        path('band/<path:object_id>/change/', dummy_view, name="test_site_band_change"),
        path('band/', dummy_view, name="test_site_band_changelist"),
        path('musician/<path:object_id>/change/', dummy_view, name="test_site_musician_change"),
        path('musician/', dummy_view, name="test_site_musician_changelist"),
        path('search/', SearchbarSearch.as_view(), name='search')
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestSearchbarSearch(DataTestCase, ViewTestCase):
    model = Band
    view_class = SearchbarSearch

    def setUp(self):
        super().setUp()
        self.queryset = Band.objects.filter(pk__in=[self.beatles.pk, self.stones.pk])

    @classmethod
    def setUpTestData(cls):
        cls.beatles = make(Band, name='The Beatles')
        cls.stones = make(Band, name='The Rolling Stones', alias='not beatles')
        cls.paul = make(Musician, name='Paul McCartney')
        cls.keith = make(Musician, name='Keith Richards')
        super().setUpTestData()

    def test_get(self):
        mock_get_results = Mock(
            return_value=[
                Band.objects.filter(pk__in=[self.beatles.pk, self.stones.pk]),
                Musician.objects.filter(pk=self.paul.pk)
            ]
        )
        with patch.object(self.view_class, 'get_results', mock_get_results):
            response = self.get_response(reverse('search'), data={'q': 'beatles'})
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertIn('total_count', data)
            self.assertEqual(data['total_count'], 3)
            self.assertIn('results', data)
            results = data['results']
            self.assertEqual(len(results), 2)  # two 'categories' (Band and Musician)
            bands, musicians = results
            self.assertEqual(
                bands,
                {
                    'category': f'<a href="/band/?id__in={self.beatles.pk},{self.stones.pk}">Bands (2)</a>',
                    'items': [
                        f'<a href="/band/{self.beatles.pk}/change/">The Beatles</a>',
                        f'<a href="/band/{self.stones.pk}/change/">The Rolling Stones</a>'
                    ]
                }
            )
            self.assertEqual(
                musicians,
                {
                    'category': f'<a href="/musician/?id__in={self.paul.pk}">Musician</a>',
                    'items': [f'<a href="/musician/{self.paul.pk}/change/">Paul McCartney</a>']
                }
            )

    def test_get_results_text_search(self):
        """Assert that get_results attempt a text search for models that support it."""
        view = self.get_view()
        with patch.object(view, 'get_models', Mock(return_value=[Band])):
            results = view.get_results('beatles')
            queryset = results[0]
            self.assertIn(self.beatles, queryset)
            # self.stones can only appear in the results when a text search
            # including the alias field was performed.
            self.assertIn(self.stones, queryset)

    def test_get_results_name_field(self):
        """
        Assert that get_results queries a model's name field if text search is
        not possible and `name_field` is set.
        """
        view = self.get_view()
        with patch.object(view, 'get_models', Mock(return_value=[Musician])):
            with patch.object(TextSearchQuery, 'search') as search_mock:
                results = view.get_results('paul')
                queryset = results[0]
                self.assertIn(self.paul, queryset)
                search_mock.assert_not_called()

    def test_get_results_no_query(self):
        """
        get_results should not perform a query if the given model does not
        support text search or does not declare a name field.
        """
        view = self.get_view(self.get_request())
        with patch.object(view, 'get_models', Mock(return_value=[Country])):
            with self.assertNumQueries(0):
                results = list(view.get_results('paul'))
            self.assertFalse(results)

    def test_get_changelist_link(self):
        view = self.get_view(self.get_request())
        self.assertEqual(
            view.get_changelist_link(self.queryset),
            f'<a href="/band/?id__in={self.beatles.pk},{self.stones.pk}">Bands (2)</a>'
        )
        self.assertEqual(
            view.get_changelist_link(self.queryset.filter(pk=self.beatles.pk)),
            f'<a href="/band/?id__in={self.beatles.pk}">Band</a>'
        )

    def test_get_changelist_link_no_permission(self):
        """
        get_changelist_link should just return a label if the user does not
        have permissions to access the changelist.
        """
        view = self.get_view(self.get_request(user=self.noperms_user))
        self.assertEqual(view.get_changelist_link(Country.objects.all()), 'Country')

    def test_get_changelist_link_blank(self):
        view = self.get_view(self.get_request(), blank=True)
        self.assertHTMLEqual(
            view.get_changelist_link(self.queryset.filter(pk=self.beatles.pk)),
            f'<a href="/band/?id__in={self.beatles.pk}" target="_blank">Band</a>'
        )
