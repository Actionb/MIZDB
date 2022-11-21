from typing import List, Tuple

from django.db import transaction
from django.db.models import Model, QuerySet

from dbentry.utils import get_model_relations


def _replace(
        obj: Model,
        attr_name: str,
        replacements: List[Model],
        related_objects: QuerySet
) -> List[Tuple[Model, str]]:
    """
    For every model instance in 'related_objects', replace the object 'obj' in
    the related set accessed via 'attr_name' with the objects given in
    'replacements'.
    """
    changes = []
    for instance in related_objects:
        related = getattr(instance, attr_name)
        if obj not in related.all():
            continue
        with transaction.atomic():
            related.remove(obj)
            related.add(*replacements)
        changes.append((instance, attr_name))
    return changes


def replace(obj: Model, replacements: List[Model]) -> List[Tuple[Model, str]]:
    """
    Walk through all reverse relations of obj and replacement any occurrence of
    it in the related sets with the objects given in replacement.
    """
    changes = []
    for rel in get_model_relations(obj._meta.model, forward=False, reverse=True):
        # if not rel.many_to_many:  # TODO: only many_to_many?
        #     continue
        related_set = getattr(obj, rel.get_accessor_name())

        changes.extend(_replace(obj, rel.remote_field.name, replacements, related_set.all()))

    obj.delete()
    return changes
