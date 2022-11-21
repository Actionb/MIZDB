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
        changes = _replace(
            self.initial, 'genre', [self.replacement1, self.replacement2], self.queryset
        )

        self.assertQuerysetEqual(
            self.band1.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(
            self.band2.genre.order_by('genre'),
            [self.extra, self.replacement1, self.replacement2]
        )
        self.assertQuerysetEqual(self.band3.genre.order_by('genre'), [self.extra])

        self.assertCountEqual(
            changes,
            [(self.band1, 'genre'), (self.band2, 'genre')]
        )

    def test_replace(self):
        changes = replace(self.initial, [self.replacement1, self.replacement2])

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

        self.assertCountEqual(
            changes,
            [(self.band1, 'genre'), (self.band2, 'genre'), (self.musiker, 'genre')]
        )

    def test_replace_rollback(self):
        """Assert that any error during the replacement results in a full rollback."""
        self.fail("Write me!")
        # TODO: fail here
        replace(self.initial, [self.replacement1, self.replacement2])
        self.assertTrue(self.model.objects.filter(pk=self.initial.pk).exists())
        self.assertTrue(self.model.objects.filter(pk=self.replacement1.pk).exists())
        self.assertTrue(self.model.objects.filter(pk=self.replacement2.pk).exists())
        self.assertQuerysetEqual(self.band1.genre.order_by('genre'), [self.initial])
        self.assertQuerysetEqual(self.band2.genre.order_by('genre'), [self.initial])
        self.assertQuerysetEqual(self.musiker.genre.order_by('genre'), [self.initial])
