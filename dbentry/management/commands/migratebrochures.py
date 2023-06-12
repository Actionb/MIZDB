from itertools import chain

from django.apps import apps
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
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

    contenttypes = {
        m: ContentType.objects.get_for_model(m)
        for m in (PrintMedia, Brochure, Kalender, Katalog, Bestand)
    }
    count = BaseBrochure.objects.count()
    log_entries = []
    for i, obj in enumerate(chain(Brochure.objects.all(), Kalender.objects.all(), Katalog.objects.all())):
        if isinstance(obj, Katalog):
            typ = type_mapping[obj.art]
        else:
            typ = type_mapping[obj._meta.model]
        if obj.beschreibung and obj.bemerkungen:
            anmerkungen = f"{obj.beschreibung}\n----\nBemerkungen: {obj.bemerkungen}"
        elif obj.bemerkungen:
            anmerkungen = f"Bemerkungen: {obj.bemerkungen}"
        else:
            anmerkungen = obj.beschreibung

        p = PrintMedia.objects.create(
            titel=obj.titel,
            typ=typ,
            zusammenfassung=obj.zusammenfassung,
            ausgabe=obj.ausgabe,
            anmerkungen=anmerkungen,
            _brochure_ptr=obj.basebrochure_ptr
        )

        # Reverse related:
        p.jahre.set((PrintMediaYear(jahr=j) for j in obj.jahre.values_list('jahr', flat=True)), bulk=False)
        p.urls.set((PrintMediaURL(url=url) for url in obj.urls.values_list('url', flat=True)), bulk=False)
        for bestand in obj.bestand_set.all():
            new_bestand = Bestand.objects.create(
                lagerort=bestand.lagerort,
                anmerkungen=bestand.anmerkungen,
                provenienz=bestand.provenienz,
                printmedia=p,
            )
            for e in LogEntry.objects.filter(object_id=bestand.pk, content_type=contenttypes[Bestand]):
                new = LogEntry(
                    action_time=e.action_time,
                    user=e.user,
                    content_type=contenttypes[Bestand],
                    object_id=new_bestand.pk,
                    object_repr=e.object_repr,
                    action_flag=e.action_flag,
                    change_message=e.change_message,
                )
                log_entries.append(new)

        # Many-to-many:
        for m2m_field in obj._meta.many_to_many:
            related = getattr(obj, m2m_field.name).all()
            if related.exists():
                getattr(p, m2m_field.name).set(related)

        for e in LogEntry.objects.filter(object_id=obj.pk, content_type=contenttypes[obj._meta.model]):
            new = LogEntry(
                action_time=e.action_time,
                user=e.user,
                content_type=contenttypes[PrintMedia],
                object_id=p.pk,
                object_repr=e.object_repr,
                action_flag=e.action_flag,
                change_message=e.change_message,
            )
            log_entries.append(new)
        print_progress(i + 1, count, prefix='Fortschritt:', suffix=f"{i + 1}/{count}")
    if log_entries:
        print("Erstelle LogEntry Objekte...")
        LogEntry.objects.bulk_create(log_entries)


class Command(BaseCommand):
    help = "Migrate the data of all (Base)Brochure objects to PrintMedia."
    requires_system_checks = [Tags.database, Tags.models]
    requires_migrations_checks = True

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
        self.stdout.write(self.style.SUCCESS("Fertig!"))
