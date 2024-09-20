from django.db import models


class Band(models.Model):
    band_name = models.CharField(max_length=100)

    def __str__(self):
        return self.band_name

    class Meta:
        verbose_name = "Band"
        verbose_name_plural = "Bands"
        ordering = ["band_name"]


class Genre(models.Model):
    genre = models.CharField(max_length=100)


class Audio(models.Model):
    titel = models.CharField(max_length=100)
    tracks = models.PositiveIntegerField("Anz. Tracks", blank=True, null=True)

    beschreibung = models.TextField(blank=True)
    bemerkungen = models.TextField(blank=True)

    band = models.ManyToManyField("test_factory.Band")
    genre = models.ManyToManyField("test_factory.Genre")

    class Meta:
        verbose_name = "Audio"


class Ancestor(models.Model):
    name = models.CharField(max_length=100, blank=True)
    ancestor = models.ForeignKey("self", on_delete=models.SET_NULL, blank=True, null=True, related_name="children")

    def __str__(self):
        return self.name


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
    magazin = models.ForeignKey("test_factory.Magazin", on_delete=models.PROTECT, related_name="ausgaben", null=True)


class Lagerort(models.Model):
    ort = models.CharField(max_length=200)

    def __str__(self):
        return self.ort


class Bestand(models.Model):
    lagerort = models.ForeignKey("test_factory.Lagerort", models.PROTECT)

    audio = models.ForeignKey("test_factory.Audio", on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return str(self.lagerort)

    class Meta:
        verbose_name = "Bestand"
