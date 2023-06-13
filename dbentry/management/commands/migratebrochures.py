from itertools import chain

from django.apps import apps
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.core.checks import Tags
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.utils import ProgrammingError

from dbentry.utils.progress import print_progress


def _create_logs(new_pk, old_pk, new_ct, old_ct):
    queryset = (
        LogEntry.objects
        .filter(object_id=old_pk, content_type=old_ct)
        .values('action_time', 'user', 'object_repr', 'action_flag', 'change_message')
    )
    return [
        LogEntry(
            action_time=e.action_time,
            user=e.user,
            content_type=new_ct,
            object_id=new_pk,
            object_repr=e.object_repr,
            action_flag=e.action_flag,
            change_message=e.change_message,
        )
        for e in queryset
    ]


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
    total = BaseBrochure.objects.count()
    new_pmedia, new_bestand = {}, {}  # map 'original object' ids to new object ids
    print("Beginne Migration...")
    for i, obj in enumerate(chain(*(
            m.objects.prefetch_related("jahre", "urls").select_related("ausgabe", "ausgabe__magazin")
            for m in (Brochure, Kalender, Katalog)
    ))):
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
        if obj.ausgabe:
            if anmerkungen:
                anmerkungen += "\n----\n"
            anmerkungen += f"Beilage von Ausgabe: {obj.ausgabe.magazin.magazin_name} {obj.ausgabe}"

        p = PrintMedia.objects.create(
            titel=obj.titel,
            typ=typ,
            zusammenfassung=obj.zusammenfassung,
            anmerkungen=anmerkungen,
            _brochure_ptr_id=obj.basebrochure_ptr_id
        )
        new_pmedia[str(obj.pk)] = p

        # Reverse related:
        p.jahre.set((PrintMediaYear(jahr=j.jahr) for j in obj.jahre.all()), bulk=False)
        p.urls.set((PrintMediaURL(url=u.url) for u in obj.urls.all()), bulk=False)
        for bestand in obj.bestand_set.values("pk", 'lagerort_id', 'anmerkungen', 'provenienz_id'):
            new = Bestand.objects.create(
                lagerort_id=bestand["lagerort_id"],
                anmerkungen=bestand["anmerkungen"],
                provenienz_id=bestand["provenienz_id"],
                printmedia=p,
            )
            new_bestand[str(bestand["pk"])] = new

        # Many-to-many:
        for m2m_field in obj._meta.many_to_many:
            related = getattr(obj, m2m_field.name).all()
            if related.exists():
                getattr(p, m2m_field.name).set(related)

        print_progress(i + 1, total, prefix="PrintMedia erstellt:", suffix=f"{i + 1}/{total}")
    if new_pmedia or new_bestand:
        print("Erstelle Admin Logs:")
        new_logentries = []
        fields = (
            "action_time", "user_id", "content_type_id", "object_id",
            "object_repr", "action_flag", "change_message"
        )
        bestand_qs = (
            LogEntry.objects
            .filter(object_id__in=new_bestand or (), content_type=contenttypes[Bestand])
            .values(*fields)
        )
        brochure_qs = (
            LogEntry.objects
            .filter(
                object_id__in=new_pmedia or (),
                content_type__in=[ct for m, ct in contenttypes.items() if m != Bestand]
            )
            .values(*fields)
        )
        total = len(brochure_qs) + len(bestand_qs)
        i = 0
        for e in chain(bestand_qs, brochure_qs):
            if e["content_type_id"] == contenttypes[Bestand].pk:
                new_obj = new_bestand[e["object_id"]]
            else:
                new_obj = new_pmedia[e["object_id"]]

            new_logentries.append(
                LogEntry(
                    action_time=e["action_time"],
                    user_id=e["user_id"],
                    content_type_id=contenttypes[new_obj._meta.model].pk,
                    object_id=new_obj.pk,
                    object_repr=e["object_repr"],
                    action_flag=e["action_flag"],
                    change_message=e["change_message"],
                )
            )
            i += 1
            print_progress(i, total, prefix="Admin Logs erstellt:", suffix=f"{i + 1}/{total}")
        if new_logentries:
            LogEntry.objects.bulk_create(new_logentries)


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
            _migrate()
        self.stdout.write(self.style.SUCCESS("Fertig!"))
