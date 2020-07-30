from DBentry import utils, models as _models
from DBentry.factory import make
from DBentry.tests.base import DataTestCase


class TestCopyRelated(DataTestCase):

    model = _models.bildmaterial
    test_data_count = 1

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.band1 = make(_models.band, band_name='Band1')
        cls.band2 = make(_models.band, band_name='Band2')

        cls.v1 = make(_models.veranstaltung, band=[cls.band1])
        cls.v2 = make(_models.veranstaltung, band=[cls.band2])
        cls.v3 = make(_models.veranstaltung)

        cls.obj1.veranstaltung.add(cls.v1, cls.v2, cls.v3)

    def test_copies_related_bands(self):
        utils.copy_related_set(self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_no_duplicates(self):
        # Assert that copy_related_set does not create duplicate related records.
        # The models actually do not allow that so we can test for an IntegrityError.
        self.obj1.band.add(self.band1)
        from django.db.utils import IntegrityError
        with self.assertNotRaises(IntegrityError):
            utils.copy_related_set(self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_preserves_own_bands(self):
        other_band = make(_models.band)
        self.obj1.band.add(other_band)

        utils.copy_related_set(self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 3)
        self.assertIn(other_band, bands)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_invalid_path(self):
        # No transactions should happen for invalid paths.
        with self.assertNumQueries(0):
            utils.copy_related_set(self.obj1, 'NOT__A__VALID__PATH')

    def test_direct_relations(self):
        # No transactions should happen for paths that represent a direct relation.
        with self.assertNumQueries(0):
            utils.copy_related_set(self.obj1, 'veranstaltung')

    def test_not_related(self):
        # If the 'target' model of the path and the 'source' model do not have a relation
        # on their own, no action should be taken.
        with self.assertNumQueries(0):
            utils.copy_related_set(self.obj1, 'veranstaltung__reihe')
