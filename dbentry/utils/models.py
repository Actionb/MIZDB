import sys
from typing import Dict, Iterable, List, Optional, Set, TextIO, Tuple, Type, Union

from django.apps import apps
from django.contrib import auth
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.db import models, transaction, utils
from django.db.models import Field, Model, constants
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel, OneToOneRel

ModelClassOrInstance = Union[Model, Type[Model]]
Relations = Union[ManyToManyRel, ManyToOneRel, OneToOneRel]
RelationalFields = Union[ForeignKey, OneToOneField]


def get_model_from_string(model_name: str, app_label: str = 'dbentry') -> Type[Model]:
    """
    Find the model class with name ``model_name``.

    Args:
        model_name (str): can either be the actual name of the model or a
            string of format: {app_label}.{model_name}
        app_label (str): the label of the app the model belongs to

    Returns:
        Model: the model class found or None, if the given app does not have a
            model with the given name.

    Raises:
        LookupError: if no application exists with this label, or no model
          exists with this name in the application
    """
    if '.' in model_name:
        app_label, model_name = model_name.split('.')
    return apps.get_model(app_label, model_name)


def get_model_fields(
        model: ModelClassOrInstance,
        base: bool = True,
        foreign: bool = True,
        m2m: bool = True,
        exclude: Iterable[str] = (),
        primary_key: bool = False
) -> List[Field]:
    """
    Return a list of concrete model fields of the given model.

    Args:
        model (Model): the model class or an instance of a model class
        base (bool): if True, non-relational fields are included
        foreign (bool): if True, ForeignKey fields are included
        m2m (bool): if True, ManyToManyFields are included
        exclude (Iterable): field names of fields to be excluded
        primary_key (bool): if True, the primary key field is included
    """
    result = []
    # noinspection PyUnresolvedReferences
    for f in model._meta.get_fields():
        if not f.concrete or f.name in exclude:
            continue
        if f.primary_key and not primary_key:
            continue
        if f.is_relation:
            if f.many_to_many:
                if m2m:
                    result.append(f)
            elif foreign:
                result.append(f)
        elif base:
            result.append(f)
    return result


def get_model_relations(
        model: ModelClassOrInstance,
        forward: bool = True,
        reverse: bool = True
) -> List[Relations]:
    """
    Return a list of relation objects that involve the given model.

    Args:
        model (Model): the model class
        forward (bool): if True, relations originating from model are included
        reverse (reverse): if True, relations towards model are included

    ManyToManyRels are considered both as forward and as reverse, and
    thus are always included.
    """
    # noinspection PyUnresolvedReferences
    intermediary_models = {
        f.remote_field.through if f.concrete else f.through
        for f in model._meta.get_fields()
        if f.many_to_many
    }

    result = []
    # noinspection PyUnresolvedReferences
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


def get_relation_info_to(
        model: ModelClassOrInstance,
        rel: Relations
) -> Tuple[Type[Model], RelationalFields]:
    """
    Return the model that implements the relation ``rel`` and the relation
    field that points towards ``model`` from that model.

    If ``rel`` is a ManyToManyRel, the relation is implemented by the
    intermediary m2m model (rel.through), and the field is the ForeignKey
    towards ``model`` on that m2m model.

    If ``rel`` is a ManyToOneRel, the returned model is rel.related_model and
    the field is the ForeignKey rel.field.

    The returned model can be queried for related objects of ``model`` using
    the name of the returned field.
    """
    # (used in utils.merge)
    if rel.many_to_many:
        related_model = rel.through
        related_opts = related_model._meta
        m2m_field = rel.field
        if m2m_field.model == model:
            # The ManyToManyField is with model:
            # the field pointing back to model on the intermediary table can
            # be retrieved via m2m_field_name().
            related_field = related_opts.get_field(m2m_field.m2m_field_name())
        else:
            # The ManyToManyField is with the *other* model:
            # the field pointing to model on the intermediary table can
            # be retrieved via m2m_reverse_field_name().
            related_field = related_opts.get_field(m2m_field.m2m_reverse_field_name())
    else:
        related_model = rel.related_model
        related_field = rel.field
    return related_model, related_field


def get_required_fields(model: ModelClassOrInstance) -> List[Field]:
    """
    Return a list of fields of that model that require an explicit value.
    (i.e. not null, no default value, etc.)
    """
    # NOTE: get_required_fields is not used
    result = []
    for f in get_model_fields(model, m2m=False):
        if f.null:
            continue
        if f.blank and isinstance(f, (models.CharField, models.TextField)):
            # String-based fields should not have null = True,
            # hence checking the less meaningful blank attribute
            continue
        if f.has_default():
            # Field has a default value, whether that value is an
            # 'EMPTY_VALUE' we do not care
            continue
        result.append(f)
    return result


def get_related_descriptor(model: ModelClassOrInstance, rel: Relations):
    """Return the ``model``'s related descriptor of relation ``rel``."""
    # NOTE: get_related_descriptor is only used by get_related_manager which
    #   itself is not used
    if rel.many_to_many:
        if rel.field.model == model:
            # model contains the ManyToManyField declaring the relation
            attr = rel.field.name
        else:
            attr = rel.get_accessor_name()
        return getattr(model, attr)
    else:
        return getattr(rel.model, rel.get_accessor_name())


def get_related_manager(instance: ModelClassOrInstance, rel: Relations):
    """
    Return the related manager that governs relation ``rel`` for model object
    ``instance``.
    """
    # NOTE: get_related_manager is not used
    # noinspection PyUnresolvedReferences
    model_class = instance._meta.model
    descriptor = get_related_descriptor(model_class, rel)
    if not rel.many_to_many and rel.field.model == model_class:
        # If rel is a forward ManyToOneRel, we must call the
        # related_manager_cls with the related object.
        return descriptor.related_manager_cls(getattr(instance, rel.field.name))
    return descriptor.related_manager_cls(instance)


def get_updatable_fields(instance: ModelClassOrInstance) -> List[str]:
    """
    Return the names of the fields that, for the given instance, are empty or
    have their default value.
    """
    # (used by merge_records)
    result = []
    # noinspection PyUnresolvedReferences
    fields = get_model_fields(
        instance._meta.model, m2m=False, primary_key=False
    )
    for fld in fields:
        if not fld.concrete or fld.name.startswith('_'):
            # Exclude 'private' fields
            continue
        field_value = fld.value_from_object(instance)
        if field_value in fld.empty_values:
            # This field's value is 'empty' in some form or other
            result.append(fld.attname)
        elif fld.has_default():
            if type(fld.default) is bool:
                # Special case, boolean values should be left alone?
                continue
            elif fld.default == field_value:
                # This field has its default value/choice
                result.append(fld.attname)
    return result


def is_protected(
        objs: List[ModelClassOrInstance],
        using: str = 'default'
) -> Optional[models.ProtectedError]:
    """
    Check if any model instances in ``objs`` is protected through a ForeignKey.

    Returns a ``models.ProtectedError`` as raised by django's deletion
    collector if an object is protected.
    """
    # (used by merge_records)
    collector = models.deletion.Collector(using=using)
    try:
        return collector.collect(objs)
    except models.ProtectedError as e:
        return e


def get_reverse_field_path(rel: Relations, field_name: str) -> str:
    """
    Build a field_path to ``field_name`` using the reverse relation ``rel``.
    """
    # (used by maint.forms.get_dupe_fields_for_model)
    if rel.related_query_name:
        field_path = rel.related_query_name
    elif rel.related_name:
        field_path = rel.related_name
    else:
        field_path = rel.related_model._meta.model_name
    return field_path + constants.LOOKUP_SEP + field_name


def get_full_fields_list(model: ModelClassOrInstance) -> Set[str]:
    """
    Collect the names of all fields and relations available on the given model.
    """
    # NOTE: get_full_fields_list is not used
    result = set()
    for field in get_model_fields(model):
        result.add(field.name)
    # Call get_model_relations with forward=False,
    # as forward relations were already added by get_model_fields.
    for rel in get_model_relations(model, forward=False):
        if rel.many_to_many and rel.field.model == model:
            result.add(rel.field.name)
        else:
            result.add(rel.name)
    return result


def get_relations_between_models(
        model1: Union[ModelClassOrInstance, str],
        model2: Union[ModelClassOrInstance, str]
) -> Optional[Tuple[RelationalFields, Relations]]:
    """
    Return the field and the relation that connects ``model1`` and ``model2``.
    """
    # NOTE: get_relations_between_models is not used
    if isinstance(model1, str):
        model1 = get_model_from_string(model1)
    if isinstance(model2, str):
        model2 = get_model_from_string(model2)

    for f in model1._meta.get_fields():  # type: ignore
        if not f.is_relation:
            continue
        if ((f.model == model1 and f.related_model == model2) or (
                f.model == model2 and f.related_model == model1)):
            if f.concrete:
                return f, f.remote_field
            else:
                return f.remote_field, f
    return None  # mypy wills it


def get_all_model_names() -> List[str]:
    """
    Return all the names of models in the apps registry that are subclasses
    of dbentry.base.models.BaseModel.
    """
    # NOTE: get_all_model_names is not used
    from dbentry.base.models import BaseModel  # avoid circular imports
    mdls = apps.get_models('dbentry')
    # noinspection PyUnresolvedReferences
    my_mdls = [m._meta.model_name for m in mdls if issubclass(m, BaseModel)]
    return sorted(my_mdls, key=lambda m: m.lower())


def get_fields_and_lookups(
        model: ModelClassOrInstance,
        field_path: str
) -> Tuple[List[Field], List[str]]:
    """
    Extract model fields and lookups from ``field_path``.

    Example: 'pizza__toppings__icontains' ->
        ([ForeignKey: pizza, CharField: toppings], ['icontains'])

    Returns:
        two lists, one containing the model fields that make up the path
            and one containing the (assumed) lookups.

    Raises:
        django.core.exceptions.FieldDoesNotExist: if a part in ``field_path``
            is not a field of ``model`` or a valid lookup.
        django.core.exceptions.FieldError: on encountering an invalid lookup.
    """
    # (used by the changelist search forms to figure out search fields)
    fields: List[Field] = []
    lookups: List[str] = []
    # noinspection PyUnresolvedReferences
    opts = model._meta
    prev_field = None
    for part in field_path.split(models.constants.LOOKUP_SEP):
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
                        'lookup': part, 'field': prev_field.__class__.__name__
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


def validate_model_data(model: Type[Model]) -> List[Tuple[Model, exceptions.ValidationError]]:
    """Validate the data of a given model."""
    # NOTE: validate_model_data is only used in validate_all_model_data which
    #   itself is not used
    invalid = []
    # noinspection PyUnresolvedReferences
    instances = list(model.objects.all())
    for instance in instances:
        try:
            instance.full_clean()
        except exceptions.ValidationError as e:
            invalid.append((instance, e))
    return invalid


def validate_all_model_data(
        *model_list: Type[Model]
) -> Dict[str, List[Tuple[Model, exceptions.ValidationError]]]:
    """
    Validate the data of given models or of all models that inherit from
    superclass dbentry.base.models.BaseModel.
    """
    # NOTE: validate_all_model_data is not used
    invalid = {}
    if not model_list:
        from dbentry.base.models import BaseModel  # avoid circular imports
        model_list = [  # type: ignore
            m for m in apps.get_models('dbentry') if issubclass(m, BaseModel)
        ]
    for model in model_list:
        # noinspection PyUnresolvedReferences
        opts = model._meta
        print("Validating %s... " % opts.model_name, end='')
        inv = validate_model_data(model)
        if inv:
            print('Invalid data found.')
            invalid[opts.model_name] = inv
        else:
            print('All data valid.')
    return invalid


def clean_contenttypes(stream: Optional[TextIO] = None) -> None:
    """Delete ContentType objects that do not refer to a model class."""
    if stream is None:
        stream = sys.stdout
    for ct in ContentType.objects.all():
        model = ct.model_class()
        if not model:
            stream.write("Deleting %s\n" % ct)
            ct.delete()


def clean_permissions(stream: Optional[TextIO] = None) -> None:
    """
    Clean up the permissions and their codenames.

    Permissions are not updated when the name of a model changes, meaning you
    can end up with two Permissions for the same action (e.g. 'add') on the
    same model but with different codenames.
    """
    if stream is None:
        stream = sys.stdout
    for p in Permission.objects.all():
        action, _model_name = p.codename.split('_', 1)
        model = p.content_type.model_class()
        if not model:
            stream.write(
                "ContentType of %s references unknown model: %s.%s\n"
                "Try running clean_contenttypes.\n" % (
                    p.name, p.content_type.app_label, p.content_type.model)
            )
            continue
        opts = model._meta
        if action not in opts.default_permissions:
            # Only update default permissions.
            continue
        old_codename = p.codename
        new_codename = auth.get_permission_codename(action, opts)
        if old_codename == new_codename:
            # Nothing to update.
            continue
        try:
            p.codename = new_codename
            with transaction.atomic():
                p.save()
        except utils.IntegrityError:
            stream.write(
                "Permission with codename '%s' already exists. "
                "Deleting permission with outdated codename: '%s'\n" % (new_codename, old_codename)
            )
            p.delete()
        else:
            stream.write(
                "Updated %s '%s' codename to '%s'\n" % (p, old_codename, new_codename)
            )
