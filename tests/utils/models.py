from django.db import models


class M2MTarget(models.Model):
    pass


class M2MSource(models.Model):
    targets = models.ManyToManyField('utils.M2MTarget', related_name='sources')


class Protector(models.Model):
    date = models.DateField(blank=True, null=True)


class Protected(models.Model):
    protector = models.ForeignKey('utils.Protector', on_delete=models.PROTECT)
