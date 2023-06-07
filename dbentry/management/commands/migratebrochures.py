from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction


def print_progress(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='█', end="\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)


    Credit: https://stackoverflow.com/a/34325723/9313033
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled = int(length * iteration // total)
    bar = fill * filled + '-' * (length - filled)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end=end)
    # Print New Line on Complete
    if iteration == total:
        print()


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

    # Get or create the base media types:
    MediaType = apps.get_model('dbentry', 'PrintMediaType')
    brochure_type = MediaType.objects.get_or_create(typ='Broschüre')[0]
    kalender_type = MediaType.objects.get_or_create(typ='Programmheft')[0]
    katalog_type = MediaType.objects.get_or_create(typ='Katalog')[0]
    type_mapping = {Brochure: brochure_type, Kalender: kalender_type, Katalog: katalog_type}

    brochures = list(BaseBrochure.objects.all())
    count = len(brochures)
    print(f"Beginne Migration von {count} Objekten...")
    for i, bb in enumerate(brochures):
        actual = bb.resolve_child()
        p = PrintMedia.objects.create(
            titel=actual.titel,
            typ=type_mapping[actual._meta.model],
            zusammenfassung=actual.zusammenfassung,
            ausgabe=actual.ausgabe,
            anmerkungen=(
                f"{actual.beschreibung}\n----{actual.bemerkungen}" if actual.bemerkungen
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
