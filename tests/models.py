from django.db import models


class Musiker(models.Model):
    kuenstler_name = models.CharField(max_length=100)

    def __str__(self):
        return self.kuenstler_name


class Band(models.Model):
    band_name = models.CharField(max_length=100)

    def __str__(self):
        return self.band_name

    class Meta:
        verbose_name = 'Band'


class Magazin(models.Model):
    magazin_name = models.CharField(max_length=100)


class Ausgabe(models.Model):
    magazin = models.ForeignKey('tests.Magazin', on_delete=models.PROTECT)


class Artikel(models.Model):
    ausgabe = models.ForeignKey('tests.Ausgabe', on_delete=models.PROTECT)


class VeranstaltungsReihe(models.Model):
    pass


class Veranstaltung(models.Model):
    name = models.CharField(max_length=100)
    reihe = models.ForeignKey(
        'tests.VeranstaltungsReihe', on_delete=models.SET_NULL, blank=True, null=True)

    musiker = models.ManyToManyField('tests.Musiker')
    band = models.ManyToManyField('tests.Band')


# Some tests require an M2M table that isn't auto created.
class MusikerAudioM2M(models.Model):
    musiker = models.ForeignKey('tests.Musiker', on_delete=models.CASCADE)
    audio = models.ForeignKey('tests.Audio', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'

    def __str__(self):
        return str(self.musiker)  # imitate dbentry.base.BaseM2MModel.__str__


class Audio(models.Model):
    titel = models.CharField(max_length=100)
    tracks = models.PositiveIntegerField('Anz. Tracks', blank=True, null=True)
    beschreibung = models.TextField(blank=True)

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

    audio = models.ForeignKey('tests.Audio', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = 'Bestand'
