from django.db import models

# TODO: when the test rework is done, re-check for unused models
from dbentry.base.models import ComputedNameModel


class Musiker(models.Model):
    kuenstler_name = models.CharField(max_length=100)

    genre = models.ManyToManyField('tests.Genre')

    def __str__(self):
        return self.kuenstler_name

    class Meta:
        verbose_name = verbose_name_plural = 'Musiker'


class Band(models.Model):
    band_name = models.CharField(max_length=100)

    genre = models.ManyToManyField('tests.Genre')
    musiker = models.ManyToManyField('tests.Musiker')

    def __str__(self):
        return self.band_name

    class Meta:
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']


class BandAlias(models.Model):
    alias = models.CharField(max_length=100)

    band = models.ForeignKey('tests.Band', on_delete=models.CASCADE)


class Magazin(models.Model):
    magazin_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.magazin_name} ({self.pk})"


class Ausgabe(models.Model):
    name = models.CharField(max_length=100)
    e_datum = models.DateField(blank=True, null=True)
    magazin = models.ForeignKey(
        'tests.Magazin', on_delete=models.PROTECT, related_name='ausgaben', null=True
    )


class Artikel(models.Model):
    schlagzeile = models.CharField(max_length=100)
    seite = models.PositiveSmallIntegerField()

    ausgabe = models.ForeignKey('tests.Ausgabe', on_delete=models.PROTECT)

    genre = models.ManyToManyField('tests.Genre')


class VeranstaltungsReihe(models.Model):
    pass


class Veranstaltung(models.Model):
    name = models.CharField(max_length=100)
    reihe = models.ForeignKey(
        'tests.VeranstaltungsReihe', on_delete=models.SET_NULL, blank=True, null=True
    )

    musiker = models.ManyToManyField('tests.Musiker')
    band = models.ManyToManyField('tests.Band')

    class Meta:
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'


# Some tests require an M2M table that isn't auto created.
class MusikerAudioM2M(models.Model):
    musiker = models.ForeignKey('tests.Musiker', on_delete=models.CASCADE)
    audio = models.ForeignKey('tests.Audio', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'
        unique_together = ('musiker', 'audio')

    def __str__(self):
        return str(self.musiker)  # imitate dbentry.base.BaseM2MModel.__str__


class Audio(models.Model):
    titel = models.CharField(max_length=100)
    tracks = models.PositiveIntegerField('Anz. Tracks', blank=True, null=True)

    beschreibung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True)

    musiker = models.ManyToManyField('tests.Musiker', through=MusikerAudioM2M)
    band = models.ManyToManyField('tests.Band')

    veranstaltung = models.ManyToManyField('tests.Veranstaltung')

    class Meta:
        verbose_name = 'Audio'


class Lagerort(models.Model):
    ort = models.CharField(max_length=200)

    def __str__(self):
        return self.ort


class Bestand(models.Model):
    lagerort = models.ForeignKey('tests.Lagerort', models.PROTECT)

    audio = models.ForeignKey('tests.Audio', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = 'Bestand'


class Ancestor(models.Model):
    name = models.CharField(max_length=100, blank=True)
    ancestor = models.ForeignKey(
        'self', on_delete=models.SET_NULL, blank=True, null=True, related_name='children'
    )

    def __str__(self):
        return self.name


class Person(ComputedNameModel):
    vorname = models.CharField(max_length=100, blank=True)
    nachname = models.CharField(max_length=100)

    name_composing_fields = ['vorname', 'nachname']

    @classmethod
    def _get_name(cls, **data):
        vorname = nachname = ''
        if 'vorname' in data:
            vorname = data['vorname'][0]
        if 'nachname' in data:
            nachname = data['nachname'][0]
        if vorname or nachname:
            return f"{vorname} {nachname}".strip()
        return "No data for Person."


class Autor(models.Model):
    kuerzel = models.CharField('Kürzel', max_length=100)
    person = models.ForeignKey('tests.Person', on_delete=models.CASCADE, null=True, blank=True)


class Genre(models.Model):
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = 'Genre'


class Base(models.Model):
    titel = models.CharField(max_length=100)

    genre = models.ManyToManyField('tests.Genre')

    def __str__(self):
        return self.titel


class Kalender(Base):
    class Meta:
        verbose_name = 'Programmheft'
