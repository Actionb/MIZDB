from django.contrib.contenttypes.models import ContentType

from dbentry import utils, models as _models
from dbentry.factory import make
from dbentry.tests.base import RequestTestCase
from dbentry.tests.mixins import LoggingTestMixin, TestDataMixin


class MergingTestCase(LoggingTestMixin, TestDataMixin, RequestTestCase):

    def setUp(self):
        super().setUp()
        # Need to clear the cache between test methods, or LogEntry queries
        # will made with wrong ContentType ids.
        ContentType.objects.clear_cache()


class TestMergingVideo(MergingTestCase):

    # Video has both auto-created (Band) and 'manual-created' (Musiker) m2m.
    model = _models.Video

    @classmethod
    def setUpTestData(cls):
        obj1 = make(
            cls.model, titel='Original', band__extra=1,
            musiker__extra=1, bestand__extra=1,
            # merge would try to update fields with default values.
            # In order to not have medium_qty show up in change messages,
            # give it a value that isn't the default.
            medium_qty=2,
        )
        cls.band_original = obj1.band.get()
        cls.musiker_original = obj1.musiker.get()
        cls.bestand_original = obj1.bestand_set.get()
        cls.original = cls.obj1 = obj1

        obj2 = make(
            cls.model, titel='Merger1', band__extra=1,
            musiker__extra=1, bestand__extra=1,
        )
        cls.band_merger1 = obj2.band.get()
        cls.musiker_merger1 = obj2.musiker.get()
        cls.bestand_merger1 = obj2.bestand_set.get()
        cls.obj2 = obj2

        obj3 = make(
            cls.model, titel='Merger2', band__extra=1,
            musiker__extra=1, bestand__extra=1,
            beschreibung='Hello!'
        )
        cls.band_merger2 = obj3.band.get()
        cls.musiker_merger2 = obj3.musiker.get()
        cls.bestand_merger2 = obj3.bestand_set.get()
        # Add a 'duplicate' related object to test handling of UNIQUE CONSTRAINTS
        # violations.
        obj3.musiker.add(cls.musiker_merger1)
        cls.obj3 = obj3

        cls.test_data = [cls.obj1, cls.obj2, cls.obj3]
        super().setUpTestData()

    def test_merge_records_expand(self):
        # Assert that merge expands the original's values with
        # expand_original=True.
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
        # Assert that merge does not expand the original's values with
        # expand_original=False.
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
        # Assert that merge adds all the related objects of the other objects
        # to original.
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

        change_message['name'] = 'Video-Musiker'
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
        # Assert that merge deletes the other objects.
        utils.merge_records(
            self.original,
            self.queryset,
            expand_original=True,
            user_id=self.super_user.pk
        )
        self.assertNotIn(self.obj2, self.model.objects.all())
        self.assertNotIn(self.obj3, self.model.objects.all())


class TestMergingProtected(MergingTestCase):

    model = _models.Ausgabe

    def test_merge(self):
        # Assert that merge handles protected relations (here: artikel) properly.
        mag = make(_models.Magazin)
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
