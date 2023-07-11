from django.db import models

from dbentry.fts.fields import SearchVectorField, WeightedColumn
from dbentry.fts.query import SIMPLE
from dbentry.query import MIZQuerySet


class Ausgabe(models.Model):
    name = models.CharField(max_length=100)

    create_field = 'name'


class Artikel(models.Model):
    ausgabe = models.ForeignKey("test_ac.Ausgabe", on_delete=models.PROTECT)


class Band(models.Model):
    band_name = models.CharField('Bandname', max_length=200)
    genre = models.ManyToManyField('test_ac.Genre')
    musiker = models.ManyToManyField('test_ac.Musiker')

    _fts = SearchVectorField(columns=[WeightedColumn('band_name', 'A', SIMPLE)])

    create_field = 'band_name'
    name_field = 'band_name'

    objects = MIZQuerySet.as_manager()

    class Meta:
        verbose_name = 'Band'
        ordering = ('band_name',)

    def __str__(self):
        return self.band_name

    @classmethod
    def overview(cls, queryset):
        return queryset


class Genre(models.Model):
    genre = models.CharField('Genre', max_length=100, unique=True)


class Musiker(models.Model):
    kuenstler_name = models.CharField('Künstlername', max_length=200)


class Base(models.Model):
    pass


class Inherited(Base):
    pass
