from typing import List

from django.db import transaction
from django.db.models import Model, QuerySet

from dbentry.utils import get_model_relations


def _replace(obj: Model, attr_name: str, replacements: List[Model], related_objects: QuerySet) -> None:
    """
    For every model instance in 'related_objects', replace the object 'obj' in
    the related set accessed via 'attr_name' with the objects given in
    'replacements'.
    """
    for instance in related_objects:
        related = getattr(instance, attr_name)
        if obj not in related.all():
            continue
        with transaction.atomic():
            related.remove(obj)
            related.add(*replacements)


def replace(obj, replacements):
    """
    Walk through all reverse relations of obj and replacement any occurrence of
    it in the related sets with the objects given in replacement.
    """
    model = obj._meta.model
    for rel in get_model_relations(model, forward=False, reverse=True):
        if not rel.many_to_many:  # TODO: only many_to_many?
            continue
        accessor = getattr(obj, rel.get_accessor_name())
        # TODO: is this distinction necessary if we only work with reverse relations?
        if accessor.reverse:
            attr = accessor.source_field_name
        else:
            attr = accessor.target_field_name

        _replace(obj, attr, replacements, accessor.all())
