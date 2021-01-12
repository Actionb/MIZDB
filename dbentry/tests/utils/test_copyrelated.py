from unittest.mock import patch

from dbentry import models as _models, admin as _admin
from django.db.utils import IntegrityError
from dbentry.factory import make
from dbentry.tests.base import AdminTestCase
from dbentry.utils import copyrelated as utils


class TestCopyRelated(AdminTestCase):

    model = _models.Bildmaterial
    model_admin_class = _admin.BildmaterialAdmin
    test_data_count = 1

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.band1 = make(_models.Band, band_name='Band1')
        cls.band2 = make(_models.Band, band_name='Band2')

        cls.v1 = make(_models.Veranstaltung, band=[cls.band1])
        cls.v2 = make(_models.Veranstaltung, band=[cls.band2])
        cls.v3 = make(_models.Veranstaltung)

        cls.obj1.veranstaltung.add(cls.v1, cls.v2, cls.v3)

    def test_copies_related_bands(self):
        utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_no_duplicates(self):
        # Assert that copy_related_set does not create duplicate related records.
        # The models actually do not allow that so we can test for an IntegrityError.
        self.obj1.band.add(self.band1)
        with self.assertNotRaises(IntegrityError):
            utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_preserves_own_bands(self):
        other_band = make(_models.Band)
        self.obj1.band.add(other_band)

        utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 3)
        self.assertIn(other_band, bands)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_invalid_path(self):
        # No transactions should happen for invalid paths.
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'NOT__A__VALID__PATH')

    def test_direct_relations(self):
        # No transactions should happen for paths that represent a direct relation.
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'veranstaltung')

    def test_not_related(self):
        # If the 'target' model of the path and the 'source' model do not have a relation
        # on their own, no action should be taken.
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'veranstaltung__reihe')

    @patch('dbentry.utils.copyrelated.create_logentry')
    def test_logentry_error(self, mocked_logentry):
        # The user should be messaged about an error during the LogEntry
        # creation, but the copy process must finish undisturbed.
        mocked_logentry.side_effect = ValueError("This is a test exception.")
        request = self.get_request()
        with self.assertNotRaises(ValueError):
            utils.copy_related_set(request, self.obj1, 'veranstaltung__band')
        # Check that copying went through:
        self.assertEqual(self.obj1.band.count(), 2)
        # Check that the message was sent:
        message_text = (
            "Fehler beim Erstellen der LogEntry Objekte: \n"
            "ValueError: This is a test exception."
        )
        self.assertMessageSent(request, message_text)
