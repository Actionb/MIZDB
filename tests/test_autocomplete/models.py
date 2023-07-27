from django.db import models


class Ausgabe(models.Model):
    name = models.CharField(max_length=100)

    name_field = "name"
    create_field = "name"
