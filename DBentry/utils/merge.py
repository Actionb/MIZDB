from django.db import transaction, models
from django.db.utils import IntegrityError

from DBentry.logging import get_logger
from DBentry.utils.models import (
    get_model_relations, get_relation_info_to, get_updateable_fields, is_protected
)


def merge_records(original, qs, update_data=None, expand_original=True, request=None):
    """
    Merges 'original' object with all other objects in 'qs' and updates
    'original's values with those in 'update_data' if 'expand_original' is True.

    Returns the updated 'original' instance.
    """
    logger = get_logger(request)
    qs = qs.exclude(pk=original.pk)
    model = original._meta.model
    original_qs = model.objects.filter(pk=original.pk)
    updateable_fields = get_updateable_fields(original)
    # Get the first value found in the other objects to replace empty values
    # of original.
    if expand_original and updateable_fields and update_data is None:
        # If updateable_fields is empty the following query will include ALL
        # values including the primary key, etc. which obviously must not be
        # allowed to happen.
        update_data = {}
        for other_record_valdict in qs.values(*updateable_fields):
            for k, v in other_record_valdict.items():
                if v and k not in update_data:
                    update_data[k] = v

    with transaction.atomic():
        # Update the original object with the additional data and log the changes.
        if expand_original and update_data:
            original_qs.update(**update_data)
            logger.log_update(original_qs, update_data)

        for rel in get_model_relations(model, forward=False):
            related_model, related_field = get_relation_info_to(model, rel)
            # Get all the related objects that are going to be updated to be
            # related to original:
            merger_related = related_model.objects.filter(
                **{related_field.name + '__in': qs}
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
                    # Since we are trying to exclude values of objects that
                    # are not yet related to original we must not call
                    # exclude(FKfield_id=original_id, <other_values>)!
                    # FKfield_id=original_id only applies to objects
                    # that are *already* related to original and thus would
                    # render the exclusion pointless.
                    unique_together = list(unique_together)
                    unique_together.remove(related_field.name)
                    if not unique_together:
                        continue
                for values in related_model.objects.filter(
                        **{related_field.name: original}
                    ).values(*unique_together):
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
                        # If an error occured, the related object will not be
                        # 'moved' to original and later deleted.
                        pass
                    else:
                        updated_ids.append(id)

            # Log the changes:
            for pk in updated_ids:
                obj = related_model.objects.get(pk=pk)
                # Log the addition of a new related object for original.
                logger.log_addition(original, obj)
                # Log the change of the related object's relation field
                # pointing towards original.
                logger.log_change(obj, related_field.name, original)

            if rel.on_delete == models.PROTECT:
                not_updated = merger_related.exclude(pk__in=updated_ids)
                if not_updated.exists() and not is_protected(not_updated):
                    # Some related objects could not be updated (probably
                    # because the original already has identical related objects).
                    # Delete the troublemakers?
                    logger.log_delete(not_updated)
                    not_updated.delete()

        # All related objects that could have been protected should now have
        # been moved to 'original' (or deleted). We can now check if any of the
        # merged objects are still protected.
        protected = is_protected(qs)
        if protected:
            # Some objects are still protected, abort the merge by forcing
            # a rollback.
            raise protected
        logger.log_delete(qs)
        qs.delete()
    return original_qs.first(), update_data
