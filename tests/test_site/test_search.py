from django.conf import settings
from django.test import override_settings
from django.urls import include, path

from dbentry.site.views.search import SearchbarSearch
from tests.case import DataTestCase, ViewTestCase
from tests.model_factory import make
from .models import Band, Musician


def dummy_view(request, *args, **kwargs):
    return None


class URLConf:
    patterns = ([
                    path('band/<path:object_id>/change/', dummy_view, name="test_site_band_change"),
                    path('band/', dummy_view, name="test_site_band_changelist"),
                    path('musician/<path:object_id>/change/', dummy_view, name="test_site_musician_change"),
                    path('musician/', dummy_view, name="test_site_musician_changelist"),
                ], 'test_site')

    urlpatterns = [
        path('', include(patterns, namespace=settings.SITE_NAMESPACE))
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestSearchbarSearch(DataTestCase, ViewTestCase):
    model = Band
    view_class = SearchbarSearch

    @classmethod
    def setUpTestData(cls):
        cls.beatles = make(Band, name='The Beatles')
        cls.stones = make(Band, name='The Rolling Stones')
        cls.paul = make(Musician, name='Paul McCartney')
        cls.keith = make(Musician, name='Keith Richards')
        super().setUpTestData()

    def test_detail_html(self):
        view = self.get_view(self.get_request())
        results = [
            Band.objects.filter(pk__in=[self.beatles.pk, self.stones.pk]),
            Musician.objects.filter(pk=self.paul.pk)
        ]
        expected = (
            '<ul>'
            f'<li><a href="/band/?id__in={self.beatles.pk},{self.stones.pk}">Bands (2)</a>'
            '<ul>'
            f'<li><a href="/band/{self.beatles.pk}/change/">The Beatles</a></li>'
            f'<li><a href="/band/{self.stones.pk}/change/">The Rolling Stones</a></li>'
            '</ul>'
            '</li>'
            f'<li><a href="/musician/?id__in={self.paul.pk}">Musician</a>'
            '<ul>'
            f'<li><a href="/musician/{self.paul.pk}/change/">Paul McCartney</a></li>'
            '</ul>'
            '</li>'
            '</ul>'
        )
        self.assertHTMLEqual(view._detail_html(results), expected)

    def test_list_html(self):
        view = self.get_view(self.get_request())
        results = [
            Band.objects.filter(pk__in=[self.beatles.pk, self.stones.pk]),
            Musician.objects.filter(pk=self.paul.pk)
        ]
        expected = (
            '<ul>'
            f'<li><a href="/band/?id__in={self.beatles.pk},{self.stones.pk}">Bands (2)</a></li>'
            f'<li><a href="/musician/?id__in={self.paul.pk}">Musician</a></li>'
            '</ul>'
        )
        self.assertHTMLEqual(view._list_html(results), expected)
