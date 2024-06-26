from django.db import models


class Genre(models.Model):
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = "Genre"
        verbose_name_plural = "Genres"


class Band(models.Model):
    class Status(models.TextChoices):
        ACTIVE = ("ACT", "Aktiv")
        INACTIVE = ("IACT", "Inaktiv")
        DISBANDED = ("DISB", "Aufgelöst")

    band_name = models.CharField("Bandname", max_length=100)
    status = models.CharField(max_length=4, choices=Status.choices, default=Status.ACTIVE)
    beschreibung = models.TextField(blank=True)
    genres = models.ManyToManyField("test_actions.Genre")

    class Meta:
        verbose_name = "Band"
        verbose_name_plural = "Bands"

    def __str__(self):
        return self.band_name


class Audio(models.Model):
    title = models.CharField("Titel", max_length=100)

    bands = models.ManyToManyField("test_actions.Band")

    class Meta:
        verbose_name = "Audio-Material"
        verbose_name_plural = "Audio-Materialien"
