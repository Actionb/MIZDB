from unittest.mock import Mock

from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from dbentry.management.commands.fix_audio_change_messages import Command
from dbentry.models import Audio, Musiker
from tests.case import UserTestCase
from tests.model_factory import make


class TestCommand(UserTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        audio_ct = ContentType.objects.get_for_model(Audio)
        cls.faulty1 = make(
            LogEntry,
            user=cls.super_user,
            content_type=audio_ct,
            object_id=1,
            object_repr="foo",
            action_flag=CHANGE,
            change_message='[{"changed": {"fields": [null]}}]',
        )
        cls.faulty2 = make(
            LogEntry,
            user=cls.super_user,
            content_type=audio_ct,
            object_id=1,
            object_repr="foo",
            action_flag=CHANGE,
            change_message='[{"changed": {"fields": ["Titel", null]}}]',
        )
        cls.faulty3 = make(
            LogEntry,
            user=cls.super_user,
            content_type=audio_ct,
            object_id=1,
            object_repr="foo",
            action_flag=CHANGE,
            change_message='[{"changed": {"fields": [null, "Quelle"]}}, {"added": {"name": "Audio-Musiker", "object": "Udo Lindenberg"}}, {"added": {"name": "Schlagwort", "object": "Single"}}]',
        )
        cls.faulty_entries = (cls.faulty1, cls.faulty2, cls.faulty3)

        cls.not_faulty = make(
            LogEntry,
            user=cls.super_user,
            content_type=audio_ct,
            object_id=1,
            object_repr="foo",
            action_flag=CHANGE,
            change_message='[{"changed": {"fields": ["Foo"]}}]',
        )
        cls.not_audio = make(
            LogEntry,
            user=cls.super_user,
            content_type=ContentType.objects.get_for_model(Musiker),
            object_id=1,
            object_repr="foo",
            action_flag=CHANGE,
            change_message='[{"changed": {"fields": [null]}}]',
        )

    def test_get_faulty_entries(self):
        """
        Assert that get_faulty_entries only returns the LogEntry objects with
        faulty change messages.
        """
        cmd = Command()
        for faulty_entry in self.faulty_entries:
            with self.subTest(faulty_entry=faulty_entry):
                faulty = cmd.get_faulty_entries()
                self.assertIn(faulty_entry, faulty)
                self.assertNotIn(self.not_faulty, faulty)

    def test_get_faulty_entries_only_audio(self):
        """Assert that only LogEntry objects of Audio objects are returned."""
        cmd = Command()
        self.assertNotIn(self.not_audio, cmd.get_faulty_entries())

    def test_fix_message(self):
        """
        Assert that fix_message replaces a 'None' object in an entry's list of
        changed fields with the string 'Laufzeit'.
        """
        test_data = [
            ('[{"changed": {"fields": [null]}}]', '[{"changed": {"fields": ["Laufzeit"]}}]'),
            ('[{"changed": {"fields": ["Titel", null]}}]', '[{"changed": {"fields": ["Titel", "Laufzeit"]}}]'),
            (
                '[{"changed": {"fields": [null, "Quelle"]}}, {"added": {"name": "Audio-Musiker", "object": "Udo Lindenberg"}}, {"added": {"name": "Schlagwort", "object": "Single"}}]',
                '[{"changed": {"fields": ["Laufzeit", "Quelle"]}}, {"added": {"name": "Audio-Musiker", "object": "Udo Lindenberg"}}, {"added": {"name": "Schlagwort", "object": "Single"}}]',
            ),
        ]
        cmd = Command()
        for change_message, expected in test_data:
            with self.subTest(change_message=change_message):
                entry = Mock(change_message=change_message)

                self.assertEqual(cmd.fix_message(entry).change_message, expected)

    def test_handle(self):
        """
        Assert that handle saves the faulty entry objects with the corrected
        change message.
        """
        fixed_messages = [
            '[{"changed": {"fields": ["Laufzeit"]}}]',
            '[{"changed": {"fields": ["Titel", "Laufzeit"]}}]',
            '[{"changed": {"fields": ["Laufzeit", "Quelle"]}}, {"added": {"name": "Audio-Musiker", "object": "Udo Lindenberg"}}, {"added": {"name": "Schlagwort", "object": "Single"}}]',
        ]
        cmd = Command()
        for fixed_message, faulty_entry in zip(fixed_messages, self.faulty_entries):
            with self.subTest(faulty_entry=faulty_entry):
                cmd.handle()
                faulty_entry.refresh_from_db()
                self.assertEqual(faulty_entry.change_message, fixed_message)
