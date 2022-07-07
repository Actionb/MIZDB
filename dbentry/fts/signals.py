from django.contrib.postgres.search import SearchVector
from django.db.models import Value
from django.db.models.signals import pre_save
from django.dispatch import receiver

from dbentry.fts.fields import SearchVectorField


def is_fts_model(model):
    if hasattr(model, '_fts'):
        return True
    return False


def get_vector(instance, search_field):
    vector = None
    for column in search_field.columns:
        v = SearchVector(
            Value(getattr(instance, column.name)), weight=column.weight, config=column.config
        )
        if vector is None:
            vector = v
        else:
            vector += v
    return vector


@receiver(pre_save, dispatch_uid="update_search_vector")
def update_search_vector_field(sender, instance, **_kwargs):
    if is_fts_model(sender):
        for field in sender._meta.get_fields():
            if isinstance(field, SearchVectorField):
                setattr(instance, field.name, get_vector(instance, field))
