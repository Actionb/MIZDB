from unittest.mock import patch

from django.db.utils import IntegrityError

from dbentry.utils import copyrelated as utils
from tests.case import DataTestCase, RequestTestCase
from tests.model_factory import make

from .models import Audio, Band, Veranstaltung


class TestCopyRelated(DataTestCase, RequestTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj1 = make(cls.model)

        b1 = cls.band1 = make(Band, band_name='Band1')
        b2 = cls.band2 = make(Band, band_name='Band2')

        v1 = make(Veranstaltung, band=[b1])
        v2 = make(Veranstaltung, band=[b2])
        v3 = make(Veranstaltung)

        cls.obj1.veranstaltung.add(v1, v2, v3)  # noqa

    def test_copies_related_bands(self):
        """copy_related_set should copy the related Band instances."""
        utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_no_duplicates(self):
        """Assert that copy_related_set does not create duplicate related records."""
        self.obj1.band.add(self.band1)
        # Attempting to create duplicates on the M2M would raise an
        # IntegrityError.
        with self.assertNotRaises(IntegrityError):
            utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 2)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_preserves_own_bands(self):
        """Assert that related objects are not dropped by the copying process."""
        other_band = make(Band)
        self.obj1.band.add(other_band)

        utils.copy_related_set(self.get_request(), self.obj1, 'veranstaltung__band')
        bands = self.obj1.band.all()
        self.assertEqual(bands.count(), 3)
        self.assertIn(other_band, bands)
        self.assertIn(self.band1, bands)
        self.assertIn(self.band2, bands)

    def test_invalid_path(self):
        """copy_related_set should not act on invalid field paths."""
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'NOT__A__VALID__PATH')

    def test_direct_relations(self):
        """
        copy_related_set should not act on field paths of direct relations;
        i.e. if the target model is related to the parent model.
        """
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'veranstaltung')

    def test_not_related(self):
        """
        copy_related_set should not act, if the source model has no relation to
        the target model defined by the path.
        """
        request = self.get_request()
        with self.assertNumQueries(0):
            utils.copy_related_set(request, self.obj1, 'veranstaltung__reihe')

    @patch('dbentry.utils.copyrelated.create_logentry')
    def test_logentry_error(self, mocked_logentry):
        """
        The user should be messaged about an error during the LogEntry creation,
        but the copy process must finish undisturbed.
        """
        mocked_logentry.side_effect = ValueError("This is a test exception.")
        # Need to touch the messages middleware - so run through all the hoops
        # by making a full request, instead of just creating a mock request
        # object via RequestFactory().
        request = self.get_response('/').wsgi_request
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
