from django.db import models


class Musiker(models.Model):
    kuenstler_name = models.CharField('Künstlername', max_length=100)
    beschreibung = models.TextField('Beschreibung', blank=True)

    person = models.ForeignKey('test_maint.Person', on_delete=models.CASCADE, null=True)
    andere = models.ForeignKey('self', on_delete=models.CASCADE, null=True)

    genres = models.ManyToManyField('test_maint.Genre')

    name_field = 'kuenstler_name'

    def __str__(self):
        return self.kuenstler_name

    class Meta:
        verbose_name = 'Musiker'


class MusikerAlias(models.Model):
    alias = models.CharField(max_length=100)
    musiker = models.ForeignKey('test_maint.Musiker', on_delete=models.CASCADE)


class Band(models.Model):
    name = models.CharField(max_length=100)

    mitglieder = models.ManyToManyField('test_maint.Musiker')


class Genre(models.Model):
    genre = models.CharField('Genre', max_length=100)

    name_field = 'genre'

    def __str__(self):
        return self.genre

    class Meta:
        verbose_name = 'Genre'


class Person(models.Model):
    name = models.CharField('Name', max_length=100)

    name_field = 'name'

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Person'


class Kalender(models.Model):
    class Meta:
        verbose_name = 'Programmheft'


class Unregistered(models.Model):
    pass
