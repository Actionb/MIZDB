from django.db import models


class Musiker(models.Model):
    kuenstler_name = models.CharField(max_length=100)

    genre = models.ManyToManyField('test_utils.Genre')

    def __str__(self):
        return self.kuenstler_name

    class Meta:
        verbose_name = verbose_name_plural = 'Musiker'


class Band(models.Model):
    band_name = models.CharField(max_length=100)

    genre = models.ManyToManyField('test_utils.Genre')
    musiker = models.ManyToManyField('test_utils.Musiker')

    def __str__(self):
        return self.band_name

    class Meta:
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']


class MusikerAudioM2M(models.Model):
    musiker = models.ForeignKey('test_utils.Musiker', on_delete=models.CASCADE)
    audio = models.ForeignKey('test_utils.Audio', on_delete=models.CASCADE)

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

    musiker = models.ManyToManyField('test_utils.Musiker', through=MusikerAudioM2M)
    band = models.ManyToManyField('test_utils.Band')

    veranstaltung = models.ManyToManyField('test_utils.Veranstaltung')

    class Meta:
        verbose_name = 'Audio'


class VeranstaltungsReihe(models.Model):
    pass


class Veranstaltung(models.Model):
    name = models.CharField(max_length=100)
    reihe = models.ForeignKey(
        'test_utils.VeranstaltungsReihe', on_delete=models.SET_NULL, blank=True, null=True
    )

    musiker = models.ManyToManyField('test_utils.Musiker')
    band = models.ManyToManyField('test_utils.Band')

    class Meta:
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'


class Lagerort(models.Model):
    ort = models.CharField(max_length=200)

    def __str__(self):
        return self.ort


class Bestand(models.Model):
    lagerort = models.ForeignKey('test_utils.Lagerort', models.PROTECT)

    audio = models.ForeignKey('test_utils.Audio', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = 'Bestand'


class Genre(models.Model):
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = 'Genre'


class Base(models.Model):
    titel = models.CharField(max_length=100)

    genre = models.ManyToManyField('test_utils.Genre')

    def __str__(self):
        return self.titel


class Kalender(Base):
    class Meta:
        verbose_name = 'Programmheft'
