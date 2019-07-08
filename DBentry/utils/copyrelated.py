from django.contrib.admin.utils import get_fields_from_path
from django.core import exceptions
from django.db import transaction

def copy_related_set(obj, *paths):
    """
    Add the related_objects in 'paths' to an equivalent relation of 'obj'.
    """
    for path in paths:
        try:
            fields = get_fields_from_path(obj, path)
            if len(fields) < 2:
                # Needs at least two degrees of separation.
                # Otherwise path will point to a set that is already
                # directly related to obj.
                continue
            target_model = fields[-1].related_model
            target_field = [
                f for f in obj._meta.get_fields() 
                if getattr(f, 'related_model', None) == target_model
            ].pop()
        except (exceptions.FieldDoesNotExist, IndexError):
            continue
        # Get the IDs of the instances to copy to obj.
        obj_qs = obj._meta.model.objects.filter(pk = obj.pk)
        none_filter = lambda i: i is not None
        ids = list(filter(none_filter, obj_qs.values_list(path, flat = True)))
        if ids:
            # Get the instances to copy to obj.
            instances = target_model.objects.filter(pk__in = ids)
            related_manager = getattr(obj, target_field.name)
            with transaction.atomic():
                related_manager.add(*instances)
