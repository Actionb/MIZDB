import io
from unittest import mock

from django.contrib.admin.models import LogEntry, CHANGE, ADDITION
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from dbentry import models as _models
from dbentry.management.commands.migratebrochures import Command
from tests.model_factory import make


class TestCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ausgabe = make(
            _models.Ausgabe, beschreibung="2023-06", sonderausgabe=True, magazin__magazin_name="Testmagazin"
        )
        # Brochure:
        cls.brochure = make(
            _models.Brochure,
            titel="Testbroschüre",
            zusammenfassung="Testbroschüre Zusammenfassung",
            beschreibung="Testbroschüre Beschreibung",
            bemerkungen="Testbroschüre Bemerkungen",
            genre__genre=["Testbroschüre Genre 1", "Testbroschüre Genre 2"],
            schlagwort__schlagwort=["Testbroschüre Schlagwort 1", "Testbroschüre Schlagwort 2"],
        )
        # Katalog (has 'art'):
        cls.katalog = make(
            _models.Katalog,
            titel="Testkatalog",
            beschreibung="Testkatalog Beschreibung",
            art=_models.Katalog.Types.TON,
        )
        # Kalender (has spielort and veranstaltung many-to-many)
        cls.spielort1 = make(_models.Spielort)
        cls.spielort2 = make(_models.Spielort)
        cls.veranstaltung1 = make(_models.Veranstaltung)
        cls.veranstaltung2 = make(_models.Veranstaltung)
        cls.kalender = make(
            _models.Kalender,
            titel="Testkalender",
            spielort=[cls.spielort1, cls.spielort2],
            veranstaltung=[cls.veranstaltung1, cls.veranstaltung2],
            bemerkungen="Kalender Bemerkungen",
        )
        # Bestand:
        cls.provenienz = make(
            _models.Provenienz,
            geber__name="Willy",
            typ=_models.Provenienz.Types.FUND,
        )
        cls.bestand1 = make(
            _models.Bestand,
            lagerort__ort="Keller",
            provenienz=cls.provenienz,
            anmerkungen="good quality",
            brochure=cls.brochure.basebrochure_ptr,
        )
        cls.bestand2 = make(_models.Bestand, lagerort__ort="Dachboden", brochure=cls.brochure.basebrochure_ptr)
        cls.user = get_user_model().objects.create_superuser(
            username="superuser", password="foobar", email="testtest@test.test"
        )

    def run_command(self):
        cmd = Command(stdout=io.StringIO())
        with mock.patch("sys.stdout"):
            cmd.handle()

    def test_command(self):
        """The command should create the expected number of PrintMedia objects."""
        self.run_command()
        queryset = _models.PrintMedia.objects
        self.assertEqual(queryset.count(), 3)

    def test_migrate_brochure(self):
        """Assert that the Brochure object was migrated as expected."""
        self.kalender.delete()
        self.katalog.delete()
        self.run_command()
        pmedia = _models.PrintMedia.objects.get(_brochure_ptr=self.brochure.pk)
        self.assertEqual(pmedia.titel, "Testbroschüre")
        self.assertEqual(pmedia.zusammenfassung, "Testbroschüre Zusammenfassung")
        self.assertEqual(pmedia.anmerkungen, "Testbroschüre Beschreibung\n----\nBemerkungen: Testbroschüre Bemerkungen")
        self.assertIn("Testbroschüre Genre 1", pmedia.genre.values_list("genre", flat=True))
        self.assertIn("Testbroschüre Genre 2", pmedia.genre.values_list("genre", flat=True))
        self.assertIn("Testbroschüre Schlagwort 1", pmedia.schlagwort.values_list("schlagwort", flat=True))
        self.assertIn("Testbroschüre Schlagwort 2", pmedia.schlagwort.values_list("schlagwort", flat=True))
        self.assertEqual(pmedia.bestand_set.count(), 2)
        self.assertCountEqual(pmedia.bestand_set.values_list("lagerort__ort", flat=True), ["Keller", "Dachboden"])
        b = pmedia.bestand_set.get(lagerort__ort="Keller")
        self.assertEqual(b.provenienz, self.provenienz)
        self.assertEqual(b.anmerkungen, "good quality")

    def test_migrate_kalender(self):
        """Assert that the Kalender object was migrated as expected."""
        self.brochure.delete()
        self.katalog.delete()
        self.run_command()
        pmedia = _models.PrintMedia.objects.get(_brochure_ptr=self.kalender.pk)
        self.assertIn(self.spielort1, pmedia.spielort.all())
        self.assertIn(self.spielort2, pmedia.spielort.all())
        self.assertIn(self.veranstaltung1, pmedia.veranstaltung.all())
        self.assertIn(self.veranstaltung2, pmedia.veranstaltung.all())
        self.assertEqual(pmedia.anmerkungen, "Bemerkungen: Kalender Bemerkungen")

    def test_migrate_katalog(self):
        """Assert that the Katalog object was migrated as expected."""
        self.brochure.delete()
        self.kalender.delete()
        self.run_command()
        pmedia = _models.PrintMedia.objects.get(_brochure_ptr=self.katalog.pk)
        self.assertEqual(pmedia.typ.typ, "Katalog (Tonträger)")
        self.assertEqual(pmedia.anmerkungen, "Testkatalog Beschreibung")

    def test_ausgabe_mentioned_in_anmerkungen(self):
        """
        Assert that the Ausgabe of the source Brochure is mentioned in the
        field 'anmerkungen'.
        """
        brochure_with_ausgabe = make(_models.Brochure, ausgabe=self.ausgabe)
        self.brochure.delete()
        self.kalender.delete()
        self.katalog.delete()
        self.run_command()
        pmedia = _models.PrintMedia.objects.get(_brochure_ptr=brochure_with_ausgabe.pk)
        self.assertIn("Beilage von Ausgabe: Testmagazin 2023-06", pmedia.anmerkungen)

    def test_logentry(self):
        def logentry_for_obj(obj, **kwargs):
            ct = ContentType.objects.get_for_model(obj)
            defaults = dict(
                user_id=self.user.id,
                content_type_id=ct.pk,
                object_id=obj.pk,
                object_repr=repr(obj),
                action_flag=CHANGE,
                change_message=f"Changed {obj}",
            )
            defaults.update(kwargs)
            return LogEntry.objects.log_action(**defaults)

        logentry_for_obj(self.brochure, action_flag=ADDITION, change_message="Added.")
        logentry_for_obj(self.brochure, action_flag=ADDITION, change_message="Added Website.")
        logentry_for_obj(self.brochure, action_flag=CHANGE, change_message="Changed Beschreibung.")
        self.kalender.delete()
        self.katalog.delete()
        self.run_command()
        logentries = LogEntry.objects.all().order_by("action_time")
        self.assertEqual(
            ["Added.", "Added Website.", "Changed Beschreibung."],
            list(logentries.values_list("change_message", flat=True)),
        )
