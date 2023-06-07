from django.apps import apps
from django.db import transaction
from django.core.management.base import BaseCommand


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

    for bb in BaseBrochure.objects.all():
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


class Command(BaseCommand):

    def handle(self, *args, **options):
        PrintMedia = apps.get_model('dbentry', 'PrintMedia')
        PrintMedia.objects.filter(_brochure_ptr__isnull=False).delete()
        _migrate()
