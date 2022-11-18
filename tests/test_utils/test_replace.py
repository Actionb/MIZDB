from dbentry.utils.replace import _replace, replace
from tests.factory import make
from .models import Band, Genre, Musiker
from ..case import DataTestCase


class TestReplace(DataTestCase):
    model = Band

    @classmethod
    def setUpTestData(cls):
        cls.initial = make(Genre, genre='initial')
        cls.replacement1 = make(Genre, genre='replacement1')
        cls.replacement2 = make(Genre, genre='replacement2')
        cls.extra = make(Genre, genre='extra')
        cls.band1 = make(Band, band_name='band1', genre=[cls.initial])  # noqa
        cls.band2 = make(Band, band_name='band2', genre=[cls.initial, cls.extra])  # noqa
        cls.band3 = make(Band, band_name='band3', genre=[cls.extra])  # noqa
        cls.musiker = make(Musiker, kuenstler_name='musiker', genre=[cls.initial])  # noqa
        super().setUpTestData()

    def test__replace(self):
        _replace(self.initial, 'genre', [self.replacement1, self.replacement2], self.queryset)
        self.assertQuerysetEqual(
            self.band1.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(
            self.band2.genre.order_by('genre'),
            [self.extra, self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(self.band3.genre.order_by('genre'), [self.extra])

    def test_replace(self):
        replace(self.initial, [self.replacement1, self.replacement2])

        self.assertQuerysetEqual(
            self.band1.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(
            self.band2.genre.order_by('genre'),
            [self.extra, self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(self.band3.genre.order_by('genre'), [self.extra])

        self.assertQuerysetEqual(
            self.musiker.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )

        self.assertFalse(Genre.objects.filter(pk=self.initial.pk).exists())
