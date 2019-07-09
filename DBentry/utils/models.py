from django.db import models

def get_model_from_string(model_name):
    from django.apps import apps 
    try:
        return apps.get_model('DBentry', model_name)
    except LookupError:
        return None

def get_model_fields(model, base = True, foreign = True, m2m = True, exclude = (), primary_key = False):
    rslt = []
    for f in model._meta.get_fields():
        if not f.concrete or f.name in exclude:
            continue
        if f.primary_key and not primary_key:
            continue
        if f.is_relation:
            if f.many_to_many:
                if m2m:
                    rslt.append(f)
            elif foreign:
                rslt.append(f)
        elif base:
            rslt.append(f)
    return rslt

def get_model_relations(model, forward = True, reverse = True):
    m2m_models = set(
        f.remote_field.through if f.concrete else f.through
        for f in model._meta.get_fields() 
        if f.many_to_many
    )

    relation_fields = [f for f in model._meta.get_fields() if f.is_relation]
    # ManyToManyRels can always be regarded as symmetrical (both 'forward' and 'reverse') and should always be included 
    #TODO: this does not maintain the order of fields/rels returned by get_fields()
    rslt = set(f.remote_field if f.concrete else f for f in relation_fields if f.many_to_many)
    for f in relation_fields:
        if f.concrete:
            if forward:
                rslt.add(f.remote_field) # add the actual RELATION, not the ForeignKey/ManyToMany field
        else:
            if not reverse:
                # We do not want any reverse relations. 
                continue
            if f.one_to_many and f.related_model in m2m_models:
                # This is a 'reverse' ForeignKey relation from an actual (i.e. not auto_created) m2m intermediary model to 'model'.
                # The relation between the intermediary model and this 'model' was realized on *both* sides, hence 
                # it shows up twice (as a ManyToOneRel and a ManyToManyRel).
                # The ManyToManyRel contains all the information we need so we ignore the ManyToOneRel.
                # If 'model' does not declare a ManyToManyField for this relation, the intermediary model would not be in 'm2m_models'.
                continue
            rslt.add(f)
    return list(rslt)

def get_relation_info_to(model, rel):
    """
    Returns:
    - the model that holds the related objects
        (rel.through if many_to_many else rel.related_model)
    - the field that realizes relation 'rel' towards direction 'model' 
        (the field of the m2m table table pointing to model if many_to_many else the ForeignKey field i.e. rel.field)
    """
    if rel.many_to_many:
        related_model = rel.through
        m2m_field = rel.field
        if m2m_field.model == model:
            # The ManyToManyField is with model:
            # the source accessor/field pointing back to model on the m2m table can be retrieved via m2m_field_name()
            related_field = related_model._meta.get_field(m2m_field.m2m_field_name())
        else:
            # The ManyToManyField is with the *other* model:
            # the related accessor/field pointing to model on the m2m table can be retrieved via m2m_reverse_field_name()
            related_field = related_model._meta.get_field(m2m_field.m2m_reverse_field_name())
    else:
        related_model = rel.related_model
        related_field = rel.field
    return related_model, related_field

def get_required_fields(model):
    """
    Returns the fields of a model that require a value.
    """
    rslt = []
    for f in get_model_fields(model, m2m = False):
        if f.null:
            continue
        if f.blank and isinstance(f, (models.CharField, models.TextField)):
            # String-based fields should not have null = True, hence checking the less meaningful blank attribute
            continue
        if f.has_default():
            # Field has a default value, whether or not that value is an 'EMPTY_VALUE' we do not care
            continue
        rslt.append(f)
    return rslt

def get_related_descriptor(model_class, rel):
    """
    Returns the descriptor that describes relation rel referenced from model model_class.
    """
    if rel.many_to_many:
        if rel.field.model == model_class:
            # model_class contains the ManyToManyField declaring the relation
            attr = rel.field.name
        else:
            attr = rel.get_accessor_name()
        descriptor = getattr(model_class, attr)
    else:
        descriptor = getattr(rel.model, rel.get_accessor_name())
    return descriptor

def get_related_manager(instance, rel):
    """
    Returns the related manager that governs the relation rel for model object instance.
    """
    descriptor = get_related_descriptor(instance._meta.model, rel)
    if not rel.many_to_many and rel.field.model == instance._meta.model:
        # If rel is a forward ManyToOneRel, we must call the related_manager_cls with the related object
        return descriptor.related_manager_cls(getattr(instance, rel.field.name))
    return descriptor.related_manager_cls(instance)

def get_updateable_fields(instance):
    """
    Returns the names of instance's fields that are empty or have their default value.
    Used by merge_records.
    """
    rslt = []
    for fld in get_model_fields(instance._meta.model, m2m = False, primary_key = False):
        if not fld.concrete or fld.name.startswith('_'):
            # Exclude 'private' fields
            continue
        field_value = fld.value_from_object(instance)
        if field_value in fld.empty_values:
            # This field's value is 'empty' in some form or other
            rslt.append(fld.attname)
        elif fld.has_default():
            if type(fld.default) is bool:
                # Special case, boolean values should be left alone?
                continue
            elif fld.default == field_value:
                # This field has it's default value/choice
                rslt.append(fld.attname)
    return rslt

def is_protected(objs, using='default'):
    """
    Returns a models.ProtectedError if any of the objs are protected through a ForeignKey, otherwise returns None.
    """
    # Used by merge_records
    collector = models.deletion.Collector(using='default')
    try:
        collector.collect(objs)
    except models.ProtectedError as e:
        return e

def get_reverse_field_path(rel, field_name):
    """
    Builds a field_path to 'field_name' using the reverse relation 'rel'. 
    """
    if rel.related_query_name:
        field_path = rel.related_query_name
    elif rel.related_name:
        field_path = rel.related_name
    else:
        field_path = rel.related_model._meta.model_name
    return field_path + models.constants.LOOKUP_SEP + field_name


def get_relations_between_models(model1, model2):
    """ 
    Returns the field and the relation object that connects model1 and model2. 
    """ 
    if isinstance(model1, str): 
        model1 = get_model_from_string(model1) 
    if isinstance(model2, str): 
        model2 = get_model_from_string(model2) 

    for f in model1._meta.get_fields():
        if not f.is_relation:
            continue
        if (f.model == model1 and f.related_model == model2) or (f.model == model2 and f.related_model == model1):
            if f.concrete:
                return f, f.remote_field
            else:
                return f.remote_field, f

def get_full_fields_list(model):
    rslt = set()
    for field in get_model_fields(model):
        rslt.add(field.name)
    for rel in get_model_relations(model, forward = False): # forward relations already handled by get_model_fields
        if rel.many_to_many and rel.field.model == model:
            rslt.add(rel.field.name)
        else:
            rslt.add(rel.name)
    return rslt

def get_all_model_names():
    """
    Returns all the names of models in the apps registry that are subclasses of DBentry.base.models.BaseModel.
    """
    from django.apps import apps 
    from DBentry.base.models import BaseModel

    mdls = apps.get_models('DBentry')
    my_mdls = [m._meta.model_name for m in mdls if issubclass(m, BaseModel)]
    return sorted(my_mdls, key = lambda m: m.lower())