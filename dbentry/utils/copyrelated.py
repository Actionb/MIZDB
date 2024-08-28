from typing import List

from django.contrib import messages
from django.contrib.admin.models import CHANGE
from django.contrib.admin.utils import get_fields_from_path
from django.core import exceptions
from django.db import transaction
from django.db.models import Model
from django.http import HttpRequest

from dbentry.utils.admin import _get_relation_change_message, create_logentry


def copy_related_set(request: HttpRequest, obj: Model, *paths: str) -> None:
    """Add the related_objects in ``paths`` to an equivalent relation of ``obj``."""
    change_message = []
    # noinspection PyUnresolvedReferences
    opts = obj._meta
    for path in paths:
        try:
            fields = get_fields_from_path(obj, path)
            if len(fields) < 2:
                # Needs at least two degrees of separation, or path will point
                # to a set that is already directly related to obj.
                continue
            target_model = fields[-1].related_model
            target_field = [f for f in opts.get_fields() if getattr(f, "related_model", None) == target_model].pop()
        except (exceptions.FieldDoesNotExist, IndexError):
            continue
        # Get the IDs of the instances to copy to obj.
        obj_qs = opts.model.objects.filter(pk=obj.pk)
        ids: List[int] = list(filter(None, obj_qs.values_list(path, flat=True)))
        if ids:
            # Get the instances to copy to obj.
            instances = target_model.objects.filter(pk__in=ids)
            related_manager = getattr(obj, target_field.name)
            with transaction.atomic():
                related_manager.add(*instances)
            for related_object in instances:
                change_message.append({"added": _get_relation_change_message(related_object, opts.model)})
    # Create LogEntry for all successful transactions.
    if change_message:
        try:
            # noinspection PyUnresolvedReferences
            create_logentry(request.user.pk, obj, CHANGE, change_message)
        except Exception as e:
            message_text = f"Fehler beim Erstellen der LogEntry Objekte: \n{e.__class__.__name__}: {e.args[0]!s}"
            messages.add_message(request=request, level=messages.ERROR, message=message_text, fail_silently=True)
