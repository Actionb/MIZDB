from django.apps import apps
from django.core import exceptions
from django.db import models


def get_model_from_string(model_name, app_label='DBentry'):
    """
    Find the model class with name 'model_name'.

    'model_name' can either be the actual name of the model or a string of
    format: '{app_label}.{model_name}'.
    Returns the model class found or None, if the given app does not have a
    model with the given name.
    """
    if '.' in model_name:
        app_label, model_name = model_name.split('.')
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


def get_model_fields(
        model, base=True, foreign=True, m2m=True, exclude=(), primary_key=False
        ):
    """
    Return a list of concrete model fields of the given model.

    Arguments that affect the contents of the result:
        base: if True, non-relational fields are included
        foreig: if True, ForeignKey fields are included
        m2m: if True, ManyToManyFields are included
        exclude: any field whose name is in this list is excluded
        primary_key: if True, the primary key field is included
    """
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


def get_model_relations(model, forward=True, reverse=True):
    """
    Return a list of relation objects that involve the given model.

    Arguments that affect the contents of the result:
        forward: if True, relations originating from 'model' are included
        reverse: if True, relations towards 'model' are included
    ManyToManyRels are always included as they are symmetrical (they can be
    considered both as forward and reverse relations).
    """
    intermediary_models = set(
        f.remote_field.through if f.concrete else f.through
        for f in model._meta.get_fields()
        if f.many_to_many
    )

    result = []
    for f in model._meta.get_fields():
        if not f.is_relation:
            continue
        if f.concrete:
            rel = f.remote_field
        else:
            rel = f

        if f.many_to_many:
            # Always add ManyToManyRels.
            pass
        elif f.concrete:
            if not forward:
                continue
        else:
            if not reverse:
                continue
            if f.one_to_many and f.related_model in intermediary_models:
                # This is a reverse ForeignKey relation from an intermediary
                # m2m model to 'model'.
                # There are two relations involved here:
                # - the ManyToOneRel from the intermediary to 'model'
                # - the ManyToManyRel through the intermediary
                # We are collecting all ManyToManyRels and this ManyToOneRel is
                # 'part' of the ManyToManyRel, so we can ignore it.
                continue
        if rel not in result:
            result.append(rel)
    return result


def get_relation_info_to(model, rel):
    """
    Return the model that implements the relation 'rel' and the model field
    that points towards 'model' from that model.

    If rel is a ManyToManyRel, the relation is implemented by the intermediary
    m2m model (rel.through) and the field is the ForeignKey towards 'model'
    on that m2m model.
    If rel is a ManyToOneRel, the returned model is rel.related_model and the
    field is the ForeignKey rel.field.
    In any case, the returned model can be queried for related objects of 'model'
    using the name of the returned field.
    """
    # (used in utils.merge)
    if rel.many_to_many:
        related_model = rel.through
        m2m_field = rel.field
        if m2m_field.model == model:
            # The ManyToManyField is with model:
            # the field pointing back to model on the intermediary table can
            # be retrieved via m2m_field_name().
            related_field = related_model._meta.get_field(
                m2m_field.m2m_field_name()
            )
        else:
            # The ManyToManyField is with the *other* model:
            # the field pointing to model on the intermediary table can
            # be retrieved via m2m_reverse_field_name().
            related_field = related_model._meta.get_field(
                m2m_field.m2m_reverse_field_name()
            )
    else:
        related_model = rel.related_model
        related_field = rel.field
    return related_model, related_field


def get_required_fields(model):
    """
    Return a list of model fields that require an explicit value.
    (i.e. not null, no default value, etc.)
    """
    # (this is not explicitly used by anything)
    rslt = []
    for f in get_model_fields(model, m2m=False):
        if f.null:
            continue
        if f.blank and isinstance(f, (models.CharField, models.TextField)):
            # String-based fields should not have null = True,
            # hence checking the less meaningful blank attribute
            continue
        if f.has_default():
            # Field has a default value, whether or not that value is an
            # 'EMPTY_VALUE' we do not care
            continue
        rslt.append(f)
    return rslt


def get_related_descriptor(model, rel):
    """Return the 'model's related descriptor of relation 'rel'."""
    # (this is not explicitly used by anything)
    if rel.many_to_many:
        if rel.field.model == model:
            # model contains the ManyToManyField declaring the relation
            attr = rel.field.name
        else:
            attr = rel.get_accessor_name()
        return getattr(model, attr)
    else:
        return getattr(rel.model, rel.get_accessor_name())


def get_related_manager(instance, rel):
    """
    Return the related manager that governs the relation 'rel' for model object
    instance.
    """
    # (this is not explicitly used by anything)
    descriptor = get_related_descriptor(instance._meta.model, rel)
    if not rel.many_to_many and rel.field.model == instance._meta.model:
        # If rel is a forward ManyToOneRel, we must call the
        # related_manager_cls with the related object.
        return descriptor.related_manager_cls(getattr(instance, rel.field.name))
    return descriptor.related_manager_cls(instance)


def get_updateable_fields(instance):
    """
    Return the names of 'instance's fields that are empty or have their default value.
    """
    # (used by merge_records)
    rslt = []
    fields = get_model_fields(instance._meta.model, m2m=False, primary_key=False)
    for fld in fields:
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
    Check if any model instances in 'objs' is protected through a ForeignKey.

    Returns a models.ProtectedError as raised by django's deletion collector
    if an object is protected.
    """
    # (used by merge_records)
    collector = models.deletion.Collector(using=using)
    try:
        collector.collect(objs)
    except models.ProtectedError as e:
        return e


def get_reverse_field_path(rel, field_name):
    """Build a field_path to 'field_name' using the reverse relation 'rel'."""
    # (used by maint.forms.get_dupe_fields_for_model)
    if rel.related_query_name:
        field_path = rel.related_query_name
    elif rel.related_name:
        field_path = rel.related_name
    else:
        field_path = rel.related_model._meta.model_name
    return field_path + models.constants.LOOKUP_SEP + field_name


def get_relations_between_models(model1, model2):
    """
    Return the field and the relation object that connects model1 and model2.
    """
    # (this is not explicitly used by anything)
    if isinstance(model1, str):
        model1 = get_model_from_string(model1)
    if isinstance(model2, str):
        model2 = get_model_from_string(model2)

    for f in model1._meta.get_fields():
        if not f.is_relation:
            continue
        if ((f.model == model1 and f.related_model == model2) or
                (f.model == model2 and f.related_model == model1)):
            if f.concrete:
                return f, f.remote_field
            else:
                return f.remote_field, f


def get_full_fields_list(model):
    """
    Collect the names of all fields and relations available on the given model.
    """
    # (this is not explicitly used by anything)
    rslt = set()
    for field in get_model_fields(model):
        rslt.add(field.name)
    # Call get_model_relations with forward=False,
    # as forward relations were already added by get_model_fields.
    for rel in get_model_relations(model, forward=False):
        if rel.many_to_many and rel.field.model == model:
            rslt.add(rel.field.name)
        else:
            rslt.add(rel.name)
    return rslt


def get_all_model_names():
    """
    Return all the names of models in the apps registry that are subclasses
    of DBentry.base.models.BaseModel.
    """
    # (this is not explicitly used by anything)
    from DBentry.base.models import BaseModel  # avoid circular imports
    mdls = apps.get_models('DBentry')
    my_mdls = [m._meta.model_name for m in mdls if issubclass(m, BaseModel)]
    return sorted(my_mdls, key=lambda m: m.lower())


def get_fields_and_lookups(model, field_path):
    """
    Extract model fields and lookups from 'field_path'.

    Raises:
        django.core.exceptions.FieldDoesNotExist: if a part in 'field_path' is
            not a field of 'model' or a valid lookup.
        django.core.exceptions.FieldError: on encountering an invalid lookup.

    Returns two lists: one containing the model fields that make up the path
    and one containing the (assumed) lookups.

    Example:
        'pizza__toppings__icontains' -> [pizza, toppings], ['icontains']
    """
    # (used by the changelist search forms to figure out search fields)
    fields, lookups = [], []
    parts = field_path.split(models.constants.LOOKUP_SEP)

    opts = model._meta
    prev_field = None
    for i, part in enumerate(parts):
        if part == 'pk':
            part = opts.pk.name
        try:
            field = opts.get_field(part)
        except exceptions.FieldDoesNotExist:
            if prev_field:
                # A valid model field was found for the previous part.
                # 'part' could be a lookup or a transform.
                if part in prev_field.get_lookups():
                    lookups.append(part)
                    continue
                raise exceptions.FieldError(
                    "Invalid lookup: %(lookup)s for %(field)s." % {
                        'lookup': part,
                        'field': prev_field.__class__.__name__
                    }
                )
            raise
        else:
            fields.append(field)
            prev_field = field
            if hasattr(field, 'get_path_info'):
                # Update opts to follow the relation.
                opts = field.get_path_info()[-1].to_opts
    return fields, lookups
