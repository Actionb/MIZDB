from django.db import models
from django.db.models import F


class Genre(models.Model):
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = "Genre"


class Band(models.Model):
    band_name = models.CharField(max_length=100)

    genre = models.ManyToManyField("test_dbentry.Genre")
    musiker = models.ManyToManyField("test_dbentry.Musiker")

    def __str__(self):
        return self.band_name

    @staticmethod
    def get_overview_annotations():
        return {"annotated": F("band_name")}

    class Meta:
        verbose_name = "Band"
        verbose_name_plural = "Bands"
        ordering = ["band_name"]


class Musiker(models.Model):
    kuenstler_name = models.CharField(max_length=100)

    genre = models.ManyToManyField("test_dbentry.Genre")

    def __str__(self):
        return self.kuenstler_name

    class Meta:
        verbose_name = verbose_name_plural = "Musiker"


class BandAlias(models.Model):
    alias = models.CharField(max_length=100)

    band = models.ForeignKey("test_dbentry.Band", on_delete=models.CASCADE)


class Artikel(models.Model):
    schlagzeile = models.CharField(max_length=100)
