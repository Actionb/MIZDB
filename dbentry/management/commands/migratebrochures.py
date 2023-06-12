from django.apps import apps
from django.core.checks import Tags
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import ProgrammingError

from dbentry.utils.progress import print_progress


# noinspection PyPep8Naming
@transaction.atomic
def _migrate():
    """Migrate all (Base)Brochure objects to the PrintMedia model."""
    PrintMedia = apps.get_model('dbentry', 'PrintMedia')
    PrintMediaYear = apps.get_model('dbentry', 'PrintMediaYear')
    PrintMediaURL = apps.get_model('dbentry', 'PrintMediaURL')
    BaseBrochure = apps.get_model('dbentry', 'BaseBrochure')
    Brochure = apps.get_model('dbentry', 'Brochure')
    Kalender = apps.get_model('dbentry', 'Kalender')
    Katalog = apps.get_model('dbentry', 'Katalog')
    Bestand = apps.get_model('dbentry', 'Bestand')

    # Get or create media types:
    MediaType = apps.get_model('dbentry', 'PrintMediaType')
    type_mapping = {
        Brochure: MediaType.objects.get_or_create(typ='Broschüre')[0],
        Kalender: MediaType.objects.get_or_create(typ='Programmheft')[0]
    }
    for art in Katalog.Types:
        type_mapping[art.value] = MediaType.objects.get_or_create(typ=f"Katalog ({art.label})")[0]

    brochures = list(BaseBrochure.objects.all())
    count = len(brochures)
    print(f"Beginne Migration von {count} Objekten...")
    for i, bb in enumerate(brochures):
        actual = bb.resolve_child()
        if isinstance(actual, Katalog):
            typ = type_mapping[actual.art]
        else:
            typ = type_mapping[actual._meta.model]
        if actual.beschreibung and actual.bemerkungen:
            anmerkungen = f"{actual.beschreibung}\n----\nBemerkungen: {actual.bemerkungen}"
        elif actual.bemerkungen:
            anmerkungen = f"Bemerkungen: {actual.bemerkungen}"
        else:
            anmerkungen = actual.beschreibung

        p = PrintMedia.objects.create(
            titel=actual.titel,
            typ=typ,
            zusammenfassung=actual.zusammenfassung,
            ausgabe=actual.ausgabe,
            anmerkungen=anmerkungen,
            _brochure_ptr=bb
        )

        # Reverse related:
        p.jahre.set((PrintMediaYear(jahr=j) for j in actual.jahre.values_list('jahr', flat=True)), bulk=False)
        p.urls.set((PrintMediaURL(url=url) for url in actual.urls.values_list('url', flat=True)), bulk=False)
        for bestand in actual.bestand_set.all():
            Bestand.objects.create(
                lagerort=bestand.lagerort,
                anmerkungen=bestand.anmerkungen,
                provenienz=bestand.provenienz,
                printmedia=p,
            )

        # Many-to-many:
        for m2m_field in actual._meta.many_to_many:
            related = getattr(actual, m2m_field.name).all()
            if related.exists():
                getattr(p, m2m_field.name).set(related)
        print_progress(i + 1, count, prefix='Fortschritt:')
    print("Fertig!")


class Command(BaseCommand):

    help = "Migrate the data of all (Base)Brochure objects to PrintMedia."
    requires_system_checks = [Tags.database, Tags.models]
    requires_migrations_checks = True

    # noinspection PyPep8Naming
    def handle(self, *args, **options):
        """Perform the data migration."""
        try:
            apps.get_model('dbentry', 'BaseBrochure')
        except LookupError:  # pragma: no cover
            self.stdout.write(self.style.ERROR("Abgebrochen: BaseBrochure model existiert nicht."))
            return

        # noinspection PyPep8Naming
        PrintMedia = apps.get_model('dbentry', 'PrintMedia')
        try:
            PrintMedia.objects.exists()
        except ProgrammingError:  # pragma: no cover
            self.stdout.write(self.style.ERROR("PrintMedia Tabelle existiert nicht."))
            return

        existing = PrintMedia.objects.filter(_brochure_ptr__isnull=False)
        with transaction.atomic():
            if existing.exists():  # pragma: no cover
                msg = (
                    f"Es existieren {existing.count()} PrintMedia Objekte, die von BaseBrochure Objekten abstammen. \n"
                    "Diese werden nun gelöscht und anschließend durch die Migration wieder neu erstellt. \n"
                    "Fortfahren? [j/N]: "
                )
                if input(msg) not in ("j", "J", "y", "Y"):
                    self.stdout.write("Abgebrochen.")
                    return
                self.stdout.write("Lösche vorhandene PrintMedia Objekte...")
                PrintMedia.objects.filter(_brochure_ptr__isnull=False).delete()
            self.stdout.write("Beginne Migration...")
            _migrate()
