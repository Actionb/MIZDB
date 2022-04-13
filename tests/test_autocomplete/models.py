from django.db import models


class Ausgabe(models.Model):
    name = models.CharField(max_length=100)

    create_field = 'name'


class Artikel(models.Model):
    ausgabe = models.ForeignKey("test_autocomplete.Ausgabe", on_delete=models.PROTECT)


class Base(models.Model):
    pass


class Inherited(Base):
    pass
