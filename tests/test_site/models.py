from django.contrib.postgres.search import SearchVector, SearchQuery
from django.db import models
from django.db.models import QuerySet

from dbentry.query import TextSearchQuerySetMixin


class TextSearchQuery(TextSearchQuerySetMixin, QuerySet):

    def search(self, q, *args, **kwargs):
        vector = SearchVector('name', 'alias')
        query = SearchQuery(q)
        return self.annotate(search=vector).filter(search=query)


class Foo(models.Model):
    bar = models.IntegerField()


class Band(models.Model):
    name = models.TextField()
    alias = models.TextField()

    objects = TextSearchQuery.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Band'
        verbose_name_plural = 'Bands'


class Country(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class Musician(models.Model):
    name = models.TextField()
    band = models.ForeignKey('test_site.Band', on_delete=models.CASCADE, null=True, blank=True)
    origin = models.ForeignKey('test_site.Country', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Musician'
        verbose_name_plural = 'Musicians'
