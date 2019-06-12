from django.contrib import admin
from django.core import exceptions
from django.db.models.constants import LOOKUP_SEP    

def get_dbfield_from_path(model, field_path):
    """
    Returns:
        - the last model field in the path 'field_path' 
        from root model 'model'
        - a list of valid lookups that were part of 'field_path'
    
    Implementation is very close to 
    django.contrib.admin.utils.get_fields_from_path
    except that it only returns the last model field found 
    and that it can handle lookups in the field_path.
    """
    pieces = field_path.split(LOOKUP_SEP)
    parent = model
    db_field, lookups = None, []
    while pieces:
        piece = pieces.pop(0)
        try:
            db_field = parent._meta.get_field(piece)
        except exceptions.FieldDoesNotExist:
            # piece is definitely not a model field;
            # but it may still be a lookup,
            # if we have previously found any db_field.
            if db_field is None:
                raise
            lookups = [piece] + pieces
            break
        try:
            parent = admin.utils.get_model_from_relation(db_field)
        except admin.utils.NotRelationField:
            # db_field is not a relation field; 
            # every piece left over should be a lookup
            lookups = pieces
            break
            
    if not db_field.concrete:
        # 'db_field' is a relation object.
        db_field = db_field.field
            
    # Check the lookups we have collected.
    unsupported = []
    for lookup in lookups:
        if lookup not in db_field.get_lookups():
            unsupported.append(lookup)
    if unsupported:
        raise exceptions.FieldError(
            "Unsupported lookup(s) '%s' for %s." % (", ".join(unsupported), db_field.__class__.__name__)
        )
    return db_field, lookups
