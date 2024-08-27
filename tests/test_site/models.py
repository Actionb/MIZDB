from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db import models
from django.db.models import QuerySet

from dbentry.query import TextSearchQuerySetMixin
from dbentry.utils.query import string_list


class TextSearchQuery(TextSearchQuerySetMixin, QuerySet):
    def search(self, q, *args, **kwargs):
        vector = SearchVector("name")
        query = SearchQuery(q)
        return self.annotate(search=vector).filter(search=query)

    def overview(self):
        return self.annotate(**self.model.get_overview_annotations()).select_related(*self.model.select_related)


class Foo(models.Model):
    bar = models.IntegerField()


class Band(models.Model):
    name = models.TextField()
    alias = models.TextField(verbose_name="Band Alias", blank=True)
    url = models.URLField(blank=True)

    origin = models.ForeignKey(
        "test_site.Country", on_delete=models.CASCADE, null=True, blank=True, verbose_name="Origin Country"
    )
    genres = models.ManyToManyField("test_site.Genre")

    objects = TextSearchQuery.as_manager()

    name_field = "name"
    select_related = ["origin"]

    @staticmethod
    def get_overview_annotations():
        return {"members_list": string_list("musician__name")}

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Band"
        verbose_name_plural = "Bands"
        default_permissions = ('add', 'change', 'delete', 'merge', 'view')


class Country(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Country"
        verbose_name_plural = "Countries"


class Musician(models.Model):
    name = models.TextField()
    band = models.ForeignKey("test_site.Band", on_delete=models.CASCADE, null=True, blank=True)
    origin = models.ForeignKey("test_site.Country", on_delete=models.CASCADE, null=True, blank=True)

    name_field = "name"

    objects = TextSearchQuery.as_manager()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Musician"
        verbose_name_plural = "Musicians"


class Genre(models.Model):
    genre = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Genre"
        verbose_name_plural = "Genres"

    def __str__(self):
        return self.genre
