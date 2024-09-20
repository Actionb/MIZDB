from django.db import models


class Band(models.Model):
    band_name = models.CharField(max_length=100)
    years_active = models.PositiveSmallIntegerField()

    genre = models.ManyToManyField("test_search.Genre")

    def __str__(self):
        return self.band_name

    class Meta:
        verbose_name = "Band"
        verbose_name_plural = "Bands"
        ordering = ["band_name"]


class Magazin(models.Model):
    magazin_name = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.magazin_name} ({self.pk})"


class Ausgabe(models.Model):
    class Status(models.TextChoices):
        UNBEARBEITET = ("unb", "unbearbeitet")
        INBEARBEITUNG = ("iB", "in Bearbeitung")
        ABGESCHLOSSEN = ("abg", "abgeschlossen")
        KEINEBEARBEITUNG = ("kB", "keine Bearbeitung vorgesehen")

    name = models.CharField(max_length=100)
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.UNBEARBEITET)
    e_datum = models.DateField(blank=True, null=True)
    magazin = models.ForeignKey("test_search.Magazin", on_delete=models.PROTECT, related_name="ausgaben", null=True)


class Genre(models.Model):
    genre = models.CharField(max_length=100)

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = "Genre"


class Artikel(models.Model):
    schlagzeile = models.CharField(max_length=100)
    seite = models.PositiveSmallIntegerField()

    ausgabe = models.ForeignKey("test_search.Ausgabe", on_delete=models.PROTECT)

    genre = models.ManyToManyField("test_search.Genre")


class Base(models.Model):
    pass


class InheritedPKModel(Base):
    pass
