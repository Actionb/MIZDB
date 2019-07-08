from django.db import transaction, models
from django.db.utils import IntegrityError

from DBentry.logging import get_logger
from DBentry.utils.models import get_model_relations, get_relation_info_to, get_updateable_fields, is_protected

def merge_records(original, qs, update_data = None, expand_original = True, request = None):
    """ Merges original object with all other objects in qs and updates original's values with those in update_data. 
        Returns the updated original.
    """
    logger = get_logger(request)

    qs = qs.exclude(pk=original.pk)
    model = original._meta.model
    original_qs = model.objects.filter(pk=original.pk)
    with transaction.atomic():
        if expand_original:
            if update_data is None:
                update_data = {} # Avoid mutable default arguments shenanigans
                updateable_fields = get_updateable_fields(original)
                for other_record_valdict in qs.values(*updateable_fields):
                    for k, v in other_record_valdict.items():
                        if v and k not in update_data:
                            update_data[k] = v

            # Update the original object with the additional data and log the changes.
            original_qs.update(**update_data)
            logger.log_update(original_qs, update_data)

        for rel in get_model_relations(model, forward = False):
            related_model, related_field = get_relation_info_to(model, rel)
            # All the related objects that are going to be updated to be related to original
            merger_related = related_model.objects.filter(**{related_field.name + '__in':qs})
            qs_to_be_updated = merger_related.all()
            if not qs_to_be_updated.exists():
                continue

            # exclude all related objects that the original has already, avoiding IntegrityError due to UNIQUE CONSTRAINT violations
            for unique_together in related_model._meta.unique_together:
                if related_field.name in unique_together:
                    # The ForeignKey field is part of this unique_together, remove it or
                    # we will later do exclude(FKfield_id=original_id,<other_values>) which would not actually exclude anything.
                    unique_together = list(unique_together)
                    unique_together.remove(related_field.name)
                    if not unique_together:
                        continue
                # Nothing will get excluded from the qs with related_field = original as no objects in the qs are related to original yet.
                for values in related_model.objects.filter(**{related_field.name:original}).values(*unique_together):
                    qs_to_be_updated = qs_to_be_updated.exclude(**values)



            # The ids of the related objects that have been updated. By default this encompasses all objects in qs_to_be_updated.
            # If an IntegrityError still occurs, this list is reevaluated.
            updated_ids = list(qs_to_be_updated.values_list('pk', flat = True))
            try:
                with transaction.atomic():
                    qs_to_be_updated.update(**{related_field.name:original})
            except IntegrityError:
                # I fucked up. An object that the original already has was left in qs_to_be_updated.
                # Work through each object in qs_to_be_updated and do the update individually.
                updated_ids = []
                for id in qs_to_be_updated.values_list('pk', flat=True):
                    loop_qs = related_model.objects.filter(pk=id)
                    try:
                        with transaction.atomic():
                            loop_qs.update(**{related_field.name:original})
                    except IntegrityError:
                        # Ignore UNIQUE CONSTRAINT violations
                        pass
                    else:
                        updated_ids.append(id)

            # Log the changes
            for id in updated_ids:
                obj = related_model.objects.get(pk=id)
                logger.log_addition(original, obj) # log the addition of a new related object for original
                logger.log_change(obj, related_field.name, original) # log the change of the related object's relation field pointing towards original

            if rel.on_delete == models.PROTECT:
                not_updated = merger_related.exclude(pk__in=updated_ids)
                if not_updated.exists() and not is_protected(not_updated):
                    # Some related objects could not be updated (probably because the original already has identical related objects)
                    # delete the troublemakers?
                    logger.log_delete(not_updated)
                    not_updated.delete()

        # All related objects that could have been protected should now have been moved to 'original'.
        # We can now check if any of the merged objects are still protected.
        protected = is_protected(qs)
        if protected:
            # Some objects are still protected, abort the merge through a rollback
            raise protected
        logger.log_delete(qs)
        qs.delete()
    return original_qs.first(), update_data
