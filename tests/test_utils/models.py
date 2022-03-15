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
    magazin = models.ForeignKey('test_utils.Magazin', on_delete=models.PROTECT)


class Artikel(models.Model):
    ausgabe = models.ForeignKey('test_utils.Ausgabe', on_delete=models.PROTECT)


class Veranstaltung(models.Model):
    name = models.CharField(max_length=100)

    musiker = models.ManyToManyField('test_utils.Musiker')
    band = models.ManyToManyField('test_utils.Band')


# Some tests require an M2M table that isn't auto created.
class MusikerAudioM2M(models.Model):
    musiker = models.ForeignKey('test_utils.Musiker', on_delete=models.CASCADE)
    audio = models.ForeignKey('test_utils.Audio', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'

    def __str__(self):
        return str(self.musiker)  # imitate dbentry.base.BaseM2MModel.__str__


class Audio(models.Model):
    titel = models.CharField(max_length=100)
    tracks = models.PositiveIntegerField('Anz. Tracks', blank=True, null=True)
    beschreibung = models.TextField(blank=True)

    musiker = models.ManyToManyField('test_utils.Musiker', through=MusikerAudioM2M)
    band = models.ManyToManyField('test_utils.Band')

    veranstaltung = models.ManyToManyField('test_utils.Veranstaltung')

    class Meta:
        verbose_name = 'Audio'


class Lagerort(models.Model):
    ort = models.CharField(max_length=200)

    def __str__(self):
        return self.ort


class Bestand(models.Model):
    lagerort = models.ForeignKey('test_utils.Lagerort', models.PROTECT)

    audio = models.ForeignKey('test_utils.Audio', on_delete=models.CASCADE)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = 'Bestand'
