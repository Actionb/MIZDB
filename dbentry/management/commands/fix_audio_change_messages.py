"""
Fix change history messages for the Audio model that include problematic 'None'
values.

Due to an oversight in dbentry.utils.admin.construct_change_message, change
messages derived from the AudioForm form would contain 'None' objects in their
list of changed fields if the 'Laufzeit' field was part of the form's changed
data. These None objects would then later cause a crash when deserializing and
translating the change message.

This command deserializes each change message of a LogEntry object for an Audio
object and replaces any None objects in the list of changed fields with a
'Laufzeit' string. The LogEntry object is then updated with that fixed change
message.
"""

import json
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import transaction

from dbentry.models import Audio


class Command(BaseCommand):
    requires_migrations_checks = True

    help = "Fix change messages for Audio objects"

    def get_faulty_entries(self):
        """
        Return the LogEntry objects that contain a 'None' object in their change
        message list of changed fields.
        """
        ct = ContentType.objects.get_for_model(Audio)
        for entry in LogEntry.objects.filter(content_type=ct).exclude(change_message="").all():
            try:
                change_message = json.loads(entry.change_message)
            except json.JSONDecodeError:
                continue
            for sub_message in change_message:
                if "changed" in sub_message:
                    for field_name in sub_message["changed"]["fields"]:
                        if field_name is None:
                            yield entry

    def fix_message(self, faulty_entry):
        """
        Given a LogEntry object, replace any 'None' objects in the entry's list
        of changed fields with the string 'Laufzeit'.
        """
        change_message = json.loads(faulty_entry.change_message)
        for sub_message in change_message:
            if "changed" in sub_message:
                for i, field_name in enumerate(sub_message["changed"]["fields"]):
                    if field_name is None:
                        sub_message["changed"]["fields"][i] = "Laufzeit"
        faulty_entry.change_message = json.dumps(change_message)
        return faulty_entry

    def handle(self, *args, **options):
        with transaction.atomic():
            for entry in self.get_faulty_entries():
                self.fix_message(entry).save()
