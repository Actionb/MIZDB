from django.db import models

from dbentry.base.models import ComputedNameModel


class UpdateCNModel(ComputedNameModel):
    name_composing_fields = ("_name",)  # use any field to suppress warnings from checks


class UpdateNormalModel(models.Model):
    pass
