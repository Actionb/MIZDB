from unittest.mock import Mock, patch

from django import forms
from django.contrib.admin.models import ADDITION, CHANGE, DELETION
from django.forms import modelform_factory
from django.test import override_settings

from dbentry.utils import admin as admin_utils
from tests.case import RequestTestCase
from tests.model_factory import make
from tests.test_utils.admin import AudioAdmin, admin_site
from tests.test_utils.models import Audio, Band, Bestand, Genre, Kalender, Lagerort, Musiker


@override_settings(ROOT_URLCONF="tests.test_utils.urls")
class TestAdminUtils(RequestTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.musiker = make(Musiker, kuenstler_name="Robert Plant")
        cls.band = make(Band, band_name="Led Zeppelin")
        cls.obj1 = obj1 = make(cls.model, titel="Testaudio")
        cls.obj2 = obj2 = make(cls.model, titel="Hovercrafts")
        lagerort = make(Lagerort, ort="Aufm Tisch!")
        cls.bestand = make(Bestand, audio=obj1, lagerort=lagerort)

        cls.test_data = [obj1, obj2]

        super().setUpTestData()

    ################################################################################################
    # test construct_change_message and _get_relation_change_message
    ################################################################################################

    def test_construct_change_message(self):
        m2m_musiker = self.obj1.musiker.through.objects.create(musiker=self.musiker, audio=self.obj1)
        m2m_band = self.obj1.band.through.objects.create(band=self.band, audio=self.obj1)

        form = modelform_factory(self.model, fields=["titel", "tracks"])()
        form.changed_data = ["tracks"]
        formsets = [
            Mock(new_objects=[m2m_musiker], changed_objects=[], deleted_objects=[]),
            Mock(new_objects=[], changed_objects=[(self.bestand, ["lagerort"])], deleted_objects=[]),
            Mock(new_objects=[], changed_objects=[], deleted_objects=[m2m_band]),
        ]

        msgs = admin_utils.construct_change_message(form, formsets, add=False)
        self.assertEqual(len(msgs), 4, msg="Expected four change messages.")
        form_msg, added_msg, changed_msg, deleted_msg = msgs
        self.assertEqual(
            form_msg["changed"]["fields"],
            ["Anz. Tracks"],
            msg="Expected the label of the changed formfield to appear in 'fields'.",
        )
        self.assertEqual(added_msg["added"], {"name": "Audio-Musiker", "object": "Robert Plant"})
        self.assertEqual(changed_msg["changed"], {"name": "Bestand", "object": "Aufm Tisch!", "fields": ["lagerort"]})
        self.assertEqual(deleted_msg["deleted"], {"name": "Band", "object": "Led Zeppelin"})

    def test_construct_change_message_added(self):
        """
        If the supplied form has no changed_data, construct_change_message
        should return a simple 'added' change message.
        """
        msg = admin_utils.construct_change_message(Mock(changed_data=None), formsets=[], add=True)
        self.assertEqual(msg, [{"added": {}}])

    def test_get_relation_change_message(self):
        """
        Assert that _get_relation_change_message uses the m2m through table
        for the change message if that table is not auto created.
        """
        m2m = self.obj1.musiker.through.objects.create(musiker=self.musiker, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict["name"], "Audio-Musiker")
        self.assertEqual(msg_dict["object"], "Robert Plant")
        with patch.object(m2m._meta, "verbose_name", new="Mocked!"):
            self.assertEqual(admin_utils._get_relation_change_message(m2m, parent_model=self.model)["name"], "Mocked!")

    def test_get_relation_change_message_auto_created(self):
        """
        Assert that for relation changes via auto created m2m tables,
        _get_relation_change_message uses verbose name and object representation
        of the object at the other end of the m2m relation.
        """
        m2m = self.obj1.band.through.objects.create(band=self.band, audio=self.obj1)
        msg_dict = admin_utils._get_relation_change_message(m2m, parent_model=self.model)
        self.assertEqual(msg_dict["name"], "Band")
        self.assertEqual(msg_dict["object"], "Led Zeppelin")

    def test_get_relation_change_message_inherited(self):
        """Assert that inherited relations are handled properly."""
        genre = make(Genre, genre="Rock")
        obj = make(Kalender, titel="Test-Programmheft")
        m2m = obj.genre.through.objects.create(genre=genre, base=obj)
        self.assertEqual(admin_utils._get_relation_change_message(m2m, Kalender), {"name": "Genre", "object": "Rock"})
        self.assertEqual(
            admin_utils._get_relation_change_message(m2m, Genre), {"name": "base", "object": "Test-Programmheft"}
        )

    def test_change_message_form_field_no_label(self):
        """
        Assert that construct_change_message properly handles form fields that
        do not have an explicit label.
        """
        # There was an issue where, if a form field did not explicitly set the
        # label attribute, construct_change_message would include a None value
        # in the list of changed fields. 'None' will then be serialized to 'null'
        # in LogEntryManager.log_action, and deserialized back to a None by
        # LogEntry.get_change_message, which will cause a crash because string
        # objects are expected here - not None objects.

        class AudioForm(forms.ModelForm):
            label = forms.CharField(label="Foo")
            no_label = forms.CharField()

            class Meta:
                model = Audio
                fields = ["titel", "label", "no_label"]

        data = {"titel": "Testaudio", "label": "foo", "no_label": "bar"}
        initial = {"label": "", "no_label": ""}
        form = AudioForm(data=data, initial=initial)
        self.assertTrue(form.is_valid(), msg=form.errors)

        change_message = admin_utils.construct_change_message(form, formsets=[], add=False)
        changed_fields = change_message[0]["changed"]["fields"]

        label = changed_fields[form.changed_data.index("label")]
        self.assertEqual(label, "Foo")
        no_label = changed_fields[form.changed_data.index("no_label")]
        self.assertIsNotNone(no_label)
        self.assertEqual(no_label, "no_label")

    ################################################################################################
    # test AdminLog helper functions
    ################################################################################################

    def test_log_addition(self):
        with patch("dbentry.utils.admin.create_logentry") as mocked_create_logentry:
            admin_utils.log_addition(
                user_id=self.super_user.pk,
                obj=self.obj1,
                related_obj=None,
            )
            expected_message = [{"added": {}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, ADDITION)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_addition_related_obj(self):
        m2m_band = self.obj1.band.through.objects.create(band=self.band, audio=self.obj1)
        with patch("dbentry.utils.admin.create_logentry") as mocked_create_logentry:
            admin_utils.log_addition(
                user_id=self.super_user.pk,
                obj=self.obj1,
                related_obj=m2m_band,
            )
            expected_message = [{"added": {"name": "Band", "object": "Led Zeppelin"}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, ADDITION)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_change(self):
        with patch("dbentry.utils.admin.create_logentry") as mocked_create_logentry:
            admin_utils.log_change(
                user_id=self.super_user.pk,
                obj=self.obj1,
                fields=["titel"],
                related_obj=None,
            )
            expected_message = [{"changed": {"fields": ["Titel"]}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, CHANGE)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_change_related_obj(self):
        m2m_band = self.obj1.band.through.objects.create(band=self.band, audio=self.obj1)
        with patch("dbentry.utils.admin.create_logentry") as mocked_create_logentry:
            admin_utils.log_change(
                user_id=self.super_user.pk,
                obj=self.obj1,
                fields=["band"],
                related_obj=m2m_band,
            )
            expected_message = [{"changed": {"fields": ["Band"], "name": "Band", "object": "Led Zeppelin"}}]
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag, message = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, CHANGE)
            self.assertIsInstance(message, list)
            self.assertEqual(message, expected_message)

    def test_log_deletion(self):
        with patch("dbentry.utils.admin.create_logentry") as mocked_create_logentry:
            admin_utils.log_deletion(user_id=self.super_user.pk, obj=self.obj1)
            self.assertTrue(mocked_create_logentry.called)
            user_id, obj, action_flag = mocked_create_logentry.call_args[0]
            self.assertEqual(user_id, self.super_user.pk)
            self.assertIsInstance(obj, self.model)
            self.assertEqual(obj, self.obj1)
            self.assertEqual(action_flag, DELETION)

    ################################################################################################
    # test get_model_admin_for_model
    ################################################################################################

    def test_get_model_admin_for_model(self):
        """
        Assert that get_model_admin_for_model returns the expected ModelAdmin
        class.
        """
        # site = AdminSite()
        # model_admin_class = type('Dummy', (ModelAdmin,), {})
        # # model_admin = ModelAdmin(self.model, site)
        # site.register(self.model, model_admin_class)
        for arg in ("test_utils.Audio", self.model):
            with self.subTest(argument=arg):
                self.assertIsInstance(
                    admin_utils.get_model_admin_for_model(arg, admin_site),
                    AudioAdmin,
                    # model_admin_class
                )

    def test_get_model_admin_for_model_not_registered(self):
        """
        get_model_admin_for_model should return None if no ModelAdmin class
        is registered with the given model.
        """
        self.assertIsNone(admin_utils.get_model_admin_for_model("test_utils.Band"), admin_site)

    def test_get_model_admin_for_model_raises_lookup_error(self):
        """
        For unknown models, get_model_admin_for_model should raise a LookupError
        (through get_model_from_string).
        """
        with self.assertRaises(LookupError):
            admin_utils.get_model_admin_for_model("beepboop")
