from django.contrib import admin
from django.core import exceptions
from django.db.models.constants import LOOKUP_SEP    

def get_fields_and_lookups_from_path(model, field_path):
    """
    Returns list of fields (using django admin's get_fields_from_path) and lookups of a given field_path.
    e.g.: 'pizza__toppings__icontains' -> [pizza, toppings], ['icontains']
    """
    fields, lookups = [], []
    path = field_path
    while path:
        try:
            fields = admin.utils.get_fields_from_path(model, path)
            break
        except (exceptions.FieldDoesNotExist, admin.utils.NotRelationField):
            # Remove the last part of the path as it may be a lookup 
            # and try again with the shortened path.
            path = path.split(LOOKUP_SEP)
            lookups.append(path.pop(-1))
            path = LOOKUP_SEP.join(path)
    return fields, list(reversed(lookups))
    
def get_dbfield_from_path(model, field_path):
    """
    Returns the final, concrete target field of a field path and the lookups used on that path.
    """
    fields, lookups = get_fields_and_lookups_from_path(model, field_path)
    if not fields:
        raise exceptions.FieldDoesNotExist(
            "%s has no field named '%s'" % (model._meta.model_name, field_path)
        )
    db_field = fields[-1]
    if not db_field.concrete: 
        # 'db_field' is a relation object.
        raise exceptions.FieldError("Reverse relations not supported.")
    return db_field, lookups
    
def validate_lookups(db_field, lookups):
    """
    Checks a list of lookups for validity for a given db field.
    """
    unsupported = []
    for lookup in lookups:
        if lookup not in db_field.get_lookups():
            unsupported.append(lookup)
    if unsupported:
        raise exceptions.FieldError(
            "Unsupported lookup(s) '%s' for %s." % (", ".join(unsupported), db_field.__class__.__name__)
        )

def strip_lookups_from_path(path, lookups):
    """
    ('datum__jahr__in', ['in']) -> 'datum__jahr'
    """
    return LOOKUP_SEP.join(
        filter(lambda piece: piece not in lookups, path.split(LOOKUP_SEP))
    )
