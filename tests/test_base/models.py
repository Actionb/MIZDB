from django.contrib.postgres.aggregates import ArrayAgg
from django.db import models
from django.db.models import F

from dbentry.base.models import BaseM2MModel, BaseModel, ComputedNameModel


# Audio, Band, Bestand, Musiker, MusikerAudioM2M, Person,
# Veranstaltung


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

    class Meta:
        verbose_name = 'Person'


class Musiker(models.Model):
    kuenstler_name = models.CharField(max_length=100)

    def __str__(self):
        return self.kuenstler_name

    class Meta:
        verbose_name = verbose_name_plural = 'Musiker'


class Band(BaseModel):
    band_name = models.CharField(max_length=100)

    def __str__(self):
        return self.band_name

    @staticmethod
    def get_overview_annotations():
        return {
            'alias_list': ArrayAgg(
                'bandalias__alias', distinct=True, ordering='bandalias__alias'
            ),
        }

    class Meta:
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'
        ordering = ['band_name']


class BandAlias(models.Model):
    alias = models.CharField(max_length=100)

    band = models.ForeignKey('test_base.Band', on_delete=models.CASCADE)


# Model for BaseM2MModel tests:
class MusikerAudioM2M(BaseM2MModel):
    audio = models.ForeignKey('test_base.Audio', on_delete=models.CASCADE)
    musiker = models.ForeignKey('test_base.Musiker', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Audio-Musiker'
        verbose_name_plural = 'Audio-Musiker'
        unique_together = ('audio', 'musiker')


class AudioReihe(BaseModel):
    name = models.CharField(max_length=50)


class Audio(BaseModel):
    titel = models.CharField(max_length=100)
    other_title = models.CharField(max_length=100, blank=True)
    tracks = models.PositiveIntegerField('Anz. Tracks', blank=True, null=True)

    beschreibung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True)

    reihe = models.ForeignKey("test_base.AudioReihe", on_delete=models.SET_NULL, blank=True, null=True)

    musiker = models.ManyToManyField('test_base.Musiker', through=MusikerAudioM2M)
    band = models.ManyToManyField('test_base.Band')

    veranstaltung = models.ManyToManyField('test_base.Veranstaltung')

    name_field = 'titel'
    exclude_from_str = ['beschreibung', 'bemerkungen']
    select_related = ("reihe",)
    prefetch_related = ("musiker",)

    @staticmethod
    def get_overview_annotations():
        return {"foo": F("titel"), "bar": F("titel")}

    class Meta(BaseModel.Meta):
        verbose_name = 'Audio'


class VeranstaltungsReihe(models.Model):
    pass


class Veranstaltung(models.Model):
    name = models.CharField(max_length=100)
    reihe = models.ForeignKey(
        'test_base.VeranstaltungsReihe', on_delete=models.SET_NULL, blank=True, null=True
    )

    musiker = models.ManyToManyField('test_base.Musiker')
    band = models.ManyToManyField('test_base.Band')

    class Meta:
        verbose_name = 'Veranstaltung'
        verbose_name_plural = 'Veranstaltungen'


class Lagerort(models.Model):
    ort = models.CharField(max_length=200)

    def __str__(self):
        return self.ort


class Bestand(models.Model):
    lagerort = models.ForeignKey('test_base.Lagerort', models.PROTECT)

    audio = models.ForeignKey('test_base.Audio', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = 'Bestand'
