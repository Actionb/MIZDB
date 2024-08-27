from dbentry.utils.replace import _replace, replace
from tests.case import DataTestCase
from tests.model_factory import make

from .models import Audio, Band, Genre, Musiker


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

        cls.audio = make(Audio, titel='audio', band=[cls.band1])  # noqa
        super().setUpTestData()

    def test__replace(self):
        changes = _replace(
            obj=self.initial,
            related_objects=self.queryset,
            attr_name='genre',
            replacements=[self.replacement1, self.replacement2]
        )

        self.assertQuerySetEqual(
            self.band1.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )
        self.assertQuerySetEqual(
            self.band2.genre.order_by('genre'),
            [self.extra, self.replacement1, self.replacement2]
        )
        self.assertQuerySetEqual(self.band3.genre.order_by('genre'), [self.extra])

        self.assertCountEqual(changes, [self.band1, self.band2])

    def test_replace(self):
        changes = replace(obj=self.initial, replacements=[self.replacement1, self.replacement2])

        self.assertQuerySetEqual(
            self.band1.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )
        self.assertQuerySetEqual(
            self.band2.genre.order_by('genre'),
            [self.extra, self.replacement1, self.replacement2]
        )
        self.assertQuerySetEqual(self.band3.genre.order_by('genre'), [self.extra])

        self.assertQuerySetEqual(
            self.musiker.genre.order_by('genre'),
            [self.replacement1, self.replacement2]
        )

        self.assertCountEqual(changes, [self.band1, self.band2, self.musiker])

    def test_replace_reverse_relation_declared_on_obj(self):
        """
        Assert that replace can handle if obj has a relation that classifies as
        'reverse' but is declared on the model of obj itself (i.e. a 'forward'
        ManyToMany).
        """
        changes = replace(self.band1, [self.band2, self.band3])
        self.assertQuerySetEqual(
            self.audio.band.order_by('band_name'),
            [self.band2, self.band3]
        )
        self.assertCountEqual(changes, [self.audio, self.initial])

    def test_replace_rollback(self):
        """Assert that any error during the replacement results in a full rollback."""
        # Calling related_set.add with an unsaved instance raises a ValueError:
        unsaved = Genre(genre='unsaved')
        with self.assertRaises(ValueError):
            _replace(
                obj=self.initial,
                related_objects=self.initial.band_set.all(),
                attr_name='genre',
                replacements=[self.replacement1, self.replacement2, unsaved]
            )
        self.assertTrue(Genre.objects.filter(pk=self.initial.pk).exists())
        self.assertTrue(Genre.objects.filter(pk=self.replacement1.pk).exists())
        self.assertTrue(Genre.objects.filter(pk=self.replacement2.pk).exists())
        self.assertQuerySetEqual(self.band1.genre.order_by('genre'), [self.initial])
        self.assertQuerySetEqual(self.band2.genre.order_by('genre'), [self.extra, self.initial])
