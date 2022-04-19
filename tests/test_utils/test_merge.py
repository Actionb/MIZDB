from django.contrib.contenttypes.models import ContentType

from dbentry import utils
from tests.case import DataTestCase, RequestTestCase
from tests.factory import make
from tests.mixins import LoggingTestMixin
from tests.models import Audio, Ausgabe, Band, Bestand, Magazin, Musiker


class MergingTestCase(LoggingTestMixin, DataTestCase, RequestTestCase):

    def setUp(self):
        super().setUp()
        # Need to clear the cache between test methods, or LogEntry queries
        # will be made with wrong ContentType ids.
        ContentType.objects.clear_cache()


class TestMerging(MergingTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.band_original = Band.objects.create(band_name='Originalband')
        cls.musiker_original = Musiker.objects.create(kuenstler_name='Originalkünstler')
        cls.obj1 = cls.original = Audio.objects.create(titel='Original')
        cls.bestand_original = make(Bestand, audio=cls.original)
        cls.original.band.add(cls.band_original)
        cls.original.musiker.add(cls.musiker_original)

        cls.band_merger1 = Band.objects.create(band_name='Mergerband One')
        cls.musiker_merger1 = Musiker.objects.create(kuenstler_name='Musikermerger One')
        cls.obj2 = Audio.objects.create(titel='Merger1')
        cls.bestand_merger1 = make(Bestand, audio=cls.obj2)
        cls.obj2.band.add(cls.band_merger1)
        cls.obj2.musiker.add(cls.musiker_merger1)

        cls.band_merger2 = Band.objects.create(band_name='Mergerband Two')
        cls.musiker_merger2 = Musiker.objects.create(kuenstler_name='Musikermerger Two')
        cls.obj3 = Audio.objects.create(titel='Merger2', beschreibung="Hello!")
        cls.bestand_merger2 = make(Bestand, audio=cls.obj3)
        cls.obj3.band.add(cls.band_merger2)
        cls.obj3.musiker.add(cls.musiker_merger2)
        # Add a 'duplicate' related object to test handling of UNIQUE CONSTRAINTS
        # violations.
        cls.obj3.musiker.add(cls.musiker_merger1)

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        super().setUpTestData()

    def test_merge_records_expand(self):
        """
        Assert that merge expands the original's values when expand_original is
        True.
        """
        new_original, update_data = utils.merge_records(
            original=self.original,
            queryset=self.queryset,
            expand_original=True,
            user_id=self.super_user.pk
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.titel, 'Original')
        self.assertEqual(new_original.beschreibung, 'Hello!')
        self.assertLoggedChange(
            new_original,
            change_message=[{'changed': {'fields': ['Beschreibung']}}]
        )

    def test_merge_records_no_expand(self):
        """
        Assert that merge does not expand the original's values when
        expand_original is False.
        """
        new_original, update_data = utils.merge_records(
            self.original,
            self.queryset,
            expand_original=False,
            user_id=self.super_user.pk
        )
        self.assertEqual(new_original, self.obj1)
        self.assertEqual(new_original.titel, 'Original')
        self.assertNotEqual(new_original.beschreibung, 'Hello!')

    def test_related_changes(self):
        """
        Assert that merge adds all the related objects of the other objects to
        the 'original'.
        """
        _new_original, _update_data = utils.merge_records(
            self.original,
            self.queryset,
            expand_original=False,
            user_id=self.super_user.pk
        )
        change_message = {"name": "", "object": ""}
        added = [{"added": change_message}]

        change_message["name"] = "Bestand"
        self.assertIn(self.bestand_original, self.obj1.bestand_set.all())
        self.assertIn(self.bestand_merger1, self.obj1.bestand_set.all())
        change_message["object"] = str(self.bestand_merger1)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertIn(self.bestand_merger2, self.obj1.bestand_set.all())
        change_message["object"] = str(self.bestand_merger2)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertEqual(self.obj1.bestand_set.all().count(), 3)

        change_message['name'] = 'Audio-Musiker'
        self.assertIn(self.musiker_original, self.obj1.musiker.all())
        self.assertIn(self.musiker_merger1, self.obj1.musiker.all())
        change_message["object"] = str(self.musiker_merger1)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertIn(self.musiker_merger2, self.obj1.musiker.all())
        change_message["object"] = str(self.musiker_merger2)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertEqual(self.obj1.musiker.all().count(), 3)

        change_message['name'] = 'Band'
        self.assertIn(self.band_original, self.obj1.band.all())
        self.assertIn(self.band_merger1, self.obj1.band.all())
        change_message["object"] = str(self.band_merger1)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertIn(self.band_merger2, self.obj1.band.all())
        change_message["object"] = str(self.band_merger2)
        self.assertLoggedAddition(self.original, change_message=str(added).replace("'", '"'))
        self.assertEqual(self.obj1.band.all().count(), 3)

    def test_rest_deleted(self):
        """Assert that merge deletes the other objects."""
        utils.merge_records(
            self.original,
            self.queryset,
            expand_original=True,
            user_id=self.super_user.pk
        )
        self.assertNotIn(self.obj2, self.model.objects.all())
        self.assertNotIn(self.obj3, self.model.objects.all())


class TestMergingProtected(MergingTestCase):
    model = Ausgabe

    def test_merge(self):
        """
        Assert that merge handles protected relations (here: artikel) properly.
        """
        mag = make(Magazin)
        obj1 = make(self.model, magazin=mag, artikel__extra=1)
        obj2 = make(self.model, magazin=mag, artikel__extra=1)
        merged, update_data = utils.merge_records(
            obj1,
            self.model.objects.all(),
            expand_original=False,
            user_id=self.super_user.pk
        )
        self.assertEqual(merged, obj1)
        self.assertEqual(merged.artikel_set.count(), 2)
        self.assertNotIn(obj2, self.model.objects.all())

    def test_raises_protected_error(self):
        # TODO: test that merge raises a protected error and rolls back the transaction when some
        #  objects are still protected
        ...
