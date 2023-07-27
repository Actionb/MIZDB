from typing import List

from django.db import transaction
from django.db.models import Model, QuerySet

from dbentry.utils import get_model_relations


def _replace(
        obj: Model,
        related_objects: QuerySet,
        attr_name: str,
        replacements: List[Model],
) -> List[Model]:
    """
    For every model instance in 'related_objects', replace the object 'obj' in
    the related set accessed via 'attr_name' with the objects given in
    'replacements'.

    Returns a list of model instances that had their relation to 'obj' replaced.
    """
    changes = []
    with transaction.atomic():
        for instance in related_objects:
            related = getattr(instance, attr_name)
            if obj in related.all():
                related.remove(obj)
                related.add(*replacements)
                changes.append(instance)
    return changes


def replace(obj: Model, replacements: List[Model]) -> List[Model]:
    """
    Replace model instance 'obj' with the instances given in 'replacements'.

    Walk through the reverse relations of 'obj' and replace any occurrence
    of it in the related sets with the objects given in 'replacements'.

    Returns a list of model instances that had their relation to 'obj' replaced.
    """
    changes = []
    for rel in get_model_relations(obj._meta.model, forward=False, reverse=True):
        if rel.related_model == obj._meta.model:
            # The relation field was declared on the model of obj;
            # the set of objects related to 'obj' is accessed via the field's
            # name. On the remote side, the accessor name gets us the set
            # to add the replacements to.
            attr_name = rel.get_accessor_name()
            related_set = getattr(obj, rel.remote_field.name)
        else:
            # The relation field was declared on the remote model.
            attr_name = rel.remote_field.name
            related_set = getattr(obj, rel.get_accessor_name())

        changes.extend(_replace(obj, related_set.all(), attr_name, replacements))

    return changes
