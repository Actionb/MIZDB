from typing import Dict, Optional, Tuple

from django.db import models, transaction
from django.db.models import Model, QuerySet
from django.db.utils import IntegrityError
from django.http import HttpRequest

from dbentry.utils.admin import log_addition, log_change, log_deletion
from dbentry.utils.models import (
    get_model_relations, get_relation_info_to, get_updatable_fields,
    is_protected
)


# noinspection  PyUnresolvedReferences
def merge_records(
        original: Model,
        queryset: QuerySet,
        update_data: Optional[Dict] = None,
        expand_original: bool = True,
        request: HttpRequest = None
) -> Tuple[Model, Optional[Dict]]:
    """
    Merge all model instances in ``queryset`` into model instance ``original``.

    Merge ``original`` object with all other objects in ``queryset`` (which
    includes combining related objects of those objects), and update
    ``original``'s values with those in ``update_data`` if ``expand_original``
    is True.

    Args:
        original (model instance): the record that other records will be merged
            into
        queryset (QuerySet): the queryset containing the other records
        update_data (dict): data to update (via queryset.update) original with
        expand_original (bool): whether to update the original with update_data
        request (HttpRequest): the request that prompted the merger; needed to
            log the changes in django's admin log/history

    Returns:
        the updated original instance and a dictionary detailing the
            updates performed on that instance.
    """
    user_id = 0
    if request:
        # TODO: REFACTOR: considering that request is only used to get at the
        #   user_id, it might be better to just pass in the user_id
        user_id = request.user.pk

    queryset = queryset.exclude(pk=original.pk)
    model = original._meta.model
    original_qs = model.objects.filter(pk=original.pk)
    updatable_fields = get_updatable_fields(original)
    # Get the first value found in the other objects to replace empty values
    # of original.
    if expand_original and updatable_fields and update_data is None:
        # If updatable_fields is empty the following query will include ALL
        # values including the primary key, etc. which obviously must not be
        # allowed to happen.
        update_data = {}
        for other_record_valdict in queryset.values(*updatable_fields):
            for k, v in other_record_valdict.items():
                if v and k not in update_data:
                    update_data[k] = v

    with transaction.atomic():
        # Update the original object with the additional data and
        # log the changes.
        if expand_original and update_data:
            original_qs.update(**update_data)
            if user_id:
                log_change(user_id, original_qs.get(), update_data.keys())

        for rel in get_model_relations(model, forward=False):
            related_model, related_field = get_relation_info_to(model, rel)
            # Get all the related objects that are going to be updated to be
            # related to original:
            merger_related = related_model.objects.filter(
                **{related_field.name + '__in': queryset}
            )
            qs_to_be_updated = merger_related.all()
            if not qs_to_be_updated.exists():
                continue

            # Exclude all related objects that the original has already to
            # avoid IntegrityErrors due to UNIQUE CONSTRAINT violations.
            for unique_together in related_model._meta.unique_together:
                if related_field.name in unique_together:
                    # The ForeignKey field that led us from original's model
                    # to this related model is part of this unique_together.
                    # Since we're filtering against this field being equal to
                    # 'original' in order to find all the values that original
                    # already has, the values of this field will always be equal
                    # to original's id.
                    # But we're trying to exclude objects that are not yet
                    # related to original (i.e. related_field.name cannot be
                    # equal to original_id), and by including this field and its
                    # values in the exclude parameters, we would exclude all
                    # those very objects that are not yet related to original.
                    # Thus, we need to remove this field from the list of
                    # parameters passed to values().
                    unique_together = list(unique_together)
                    unique_together.remove(related_field.name)
                    if not unique_together:
                        continue
                for values in (
                        related_model.objects
                        .filter(**{related_field.name: original})
                        .values(*unique_together)
                ):
                    # Exclude all values that would violate the unique
                    # constraints (i.e. values that original has already):
                    qs_to_be_updated = qs_to_be_updated.exclude(**values)

            # Get the ids of the related objects that will be updated.
            # If an IntegrityError occurs, despite our efforts above,
            # this list is reevaluated.
            updated_ids = list(qs_to_be_updated.values_list('pk', flat=True))
            try:
                with transaction.atomic():
                    qs_to_be_updated.update(**{related_field.name: original})
            except IntegrityError:
                # An object that the original already has was left in
                # qs_to_be_updated. Work through each object in
                # qs_to_be_updated and do the update individually.
                updated_ids = []
                for pk in qs_to_be_updated.values_list('pk', flat=True):
                    loop_qs = related_model.objects.filter(pk=pk)
                    try:
                        with transaction.atomic():
                            loop_qs.update(**{related_field.name: original})
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations at this stage.
                        # If an error occurred, the related object will not be
                        # 'moved' to original and later deleted.
                        pass
                    else:
                        updated_ids.append(pk)

            # Log the changes:
            for pk in updated_ids:
                obj = related_model.objects.get(pk=pk)
                if user_id:
                    # Log the addition of a new related object for original.
                    log_addition(user_id, original, obj)
                    # Log the change of the related object's relation field
                    # pointing towards original.
                    log_change(user_id, obj, related_field.name)

            if rel.on_delete == models.PROTECT:
                not_updated = merger_related.exclude(pk__in=updated_ids)
                if not_updated.exists() and not is_protected(not_updated):
                    # Some related objects could not be updated (probably
                    # because the original already has identical related objects).
                    # Delete the troublemakers?
                    if user_id:
                        for obj in not_updated:
                            log_deletion(user_id, obj)
                    not_updated.delete()

        # All related objects that could have been protected should now have
        # been moved to 'original' (or deleted). We can now check if any of the
        # merged objects are still protected.
        protected = is_protected(queryset)
        if protected:
            # Some objects are still protected, abort the merge by forcing
            # a rollback.
            raise protected
        if user_id:
            for obj in queryset:
                log_deletion(user_id, obj)
        queryset.delete()
    return original_qs.first(), update_data
