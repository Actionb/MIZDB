from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

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
        p = PrintMedia.objects.create(
            titel=actual.titel,
            typ=typ,
            zusammenfassung=actual.zusammenfassung,
            ausgabe=actual.ausgabe,
            anmerkungen=(
                f"{actual.beschreibung}\n----\n{actual.bemerkungen}" if actual.bemerkungen
                else actual.beschreibung
            ),
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

    def handle(self, *args, **options):
        print()
        # noinspection PyPep8Naming
        PrintMedia = apps.get_model('dbentry', 'PrintMedia')
        existing = PrintMedia.objects.filter(_brochure_ptr__isnull=False)
        if existing.exists():
            msg = (
                f"Es existieren {existing.count()} PrintMedia Objekte, die von BaseBrochure "
                "Objekten abstammen. Diese werden nun gelöscht.  Fortfahren? [j/N]: "
            )
            if input(msg) not in ("j", "J", "y", "Y"):
                print("Abgebrochen.")
                return
        print("Lösche vorhandene PrintMedia Objekte...")
        PrintMedia.objects.filter(_brochure_ptr__isnull=False).delete()
        _migrate()
