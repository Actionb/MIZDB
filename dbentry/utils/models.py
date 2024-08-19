import sys
from typing import Iterable, List, Optional, TextIO, Tuple, Type, Union, Sequence

from django.apps import apps
from django.contrib import auth
from django.contrib.admin.utils import NestedObjects
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core import exceptions
from django.db import models, transaction, utils
from django.db.models import Field, Model, constants, QuerySet
from django.db.models.fields.related import ForeignKey, OneToOneField
from django.db.models.fields.reverse_related import ManyToManyRel, ManyToOneRel, OneToOneRel
from django.http import HttpRequest
from django.urls import NoReverseMatch
from django.utils.safestring import mark_safe
from django.utils.text import capfirst

from dbentry.utils.html import create_hyperlink
from dbentry.utils.permission import get_perm
from dbentry.utils.url import get_change_url

ModelClassOrInstance = Union[Model, Type[Model]]
Relations = Union[ManyToManyRel, ManyToOneRel, OneToOneRel]
RelationalFields = Union[ForeignKey, OneToOneField]


def get_model_from_string(model_name: str, app_label: str = "dbentry") -> Type[Model]:
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
    if "." in model_name:
        app_label, model_name = model_name.split(".")
    return apps.get_model(app_label, model_name)


def get_model_fields(
    model: ModelClassOrInstance,
    base: bool = True,
    foreign: bool = True,
    m2m: bool = True,
    exclude: Iterable[str] = (),
    primary_key: bool = False,
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


def get_model_relations(model: ModelClassOrInstance, forward: bool = True, reverse: bool = True) -> List[Relations]:
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
        f.remote_field.through if f.concrete else f.through for f in model._meta.get_fields() if f.many_to_many
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


def get_relation_info_to(model: ModelClassOrInstance, rel: Relations) -> Tuple[Type[Model], RelationalFields]:
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


def get_updatable_fields(instance: ModelClassOrInstance) -> List[str]:
    """
    Return the names of the fields that, for the given instance, are empty or
    have their default value.
    """
    # (used by merge_records)
    result = []
    # noinspection PyUnresolvedReferences
    fields = get_model_fields(instance._meta.model, m2m=False, primary_key=False)
    for fld in fields:
        if not fld.concrete or fld.name.startswith("_"):
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


def is_protected(objs: List[ModelClassOrInstance], using: str = "default") -> Optional[models.ProtectedError]:
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
    # (used by dbentry.tools.forms.get_dupe_field_choices)
    if rel.related_query_name:
        field_path = rel.related_query_name
    elif rel.related_name:
        field_path = rel.related_name
    else:
        field_path = rel.related_model._meta.model_name
    return field_path + constants.LOOKUP_SEP + field_name


def get_fields_and_lookups(model: ModelClassOrInstance, field_path: str) -> Tuple[List[Field], List[str]]:
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
        if part == "pk":
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
                    "Invalid lookup: %(lookup)s for %(field)s."
                    % {"lookup": part, "field": prev_field.__class__.__name__}
                )
            raise
        else:
            fields.append(field)
            prev_field = field
            if hasattr(field, "get_path_info"):
                # Update opts to follow the relation.
                opts = field.get_path_info()[-1].to_opts
    return fields, lookups


def clean_contenttypes(stream: Optional[TextIO] = None) -> None:
    """Delete ContentType objects that do not refer to a model class."""
    if stream is None:  # pragma: no cover
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
    if stream is None:  # pragma: no cover
        stream = sys.stdout
    for p in Permission.objects.all():
        action, _model_name = p.codename.split("_", 1)
        model = p.content_type.model_class()
        if not model:
            stream.write(
                "ContentType of %s references unknown model: %s.%s\n"
                "Try running clean_contenttypes.\n" % (p.name, p.content_type.app_label, p.content_type.model)
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
            stream.write("Updated %s '%s' codename to '%s'\n" % (p, old_codename, new_codename))


def get_deleted_objects(
    request: HttpRequest,
    objs: Union[Sequence[models.Model], QuerySet],
    namespace: str = "",
) -> tuple[list, dict, set, list]:
    """
    Find all objects related to ``objs`` that should also be deleted. ``objs``
    must be a homogeneous sequence of objects (e.g. a QuerySet).

    Returns a 4-tuple:
        - a nested list of string representations of objects that will be
          deleted as returned by the NestedObjects collector
        - a mapping of model verbose name to the number of objects belonging
          to that model that will be deleted
        - a set of model verbose names of models for which the user is lacking
          delete permission
        - a list of string representations of model objects that are protected
          by a relation
    """
    # Modified version of django.contrib.admin.utils.get_deleted_objects with
    # better description for relations and related objects.
    origin_model = objs[0].__class__
    collector = NestedObjects(using="default", origin=objs)
    collector.collect(objs)
    perms_needed = set()

    def get_related_obj_info(obj: models.Model) -> tuple[models.Model, str, str]:
        related_obj = obj
        obj_verbose_name = capfirst(obj._meta.verbose_name)
        obj_description = str(obj)
        if obj._meta.auto_created:
            # Assume an auto_created M2M model with a generic verbose_name.
            # To get a better verbose_name, figure out from what side we
            # are deleting and use the other side's verbose name.
            for field in obj._meta.get_fields():
                if field.is_relation and field.related_model != origin_model:
                    other_pk = field.value_from_object(obj)
                    # FIXME: this is incredibly inefficient as it creates a
                    #  query for every related object!
                    related_obj = field.related_model.objects.get(pk=other_pk)
                    obj_description = str(related_obj)
                    obj_verbose_name = f"{field.related_model._meta.verbose_name} Beziehung"
                    break
        return related_obj, obj_verbose_name, obj_description

    def format_callback(obj: models.Model) -> str:
        related_obj, obj_verbose_name, obj_description = get_related_obj_info(obj)

        try:
            # Try to get a link to the object's edit page.
            obj_description = create_hyperlink(get_change_url(request, related_obj, namespace), obj_description)
            if not obj._meta.auto_created and not request.user.has_perm(get_perm("delete", obj._meta)):
                perms_needed.add(obj_verbose_name)
        except NoReverseMatch:
            # obj has no edit page.
            pass
        return mark_safe(f"{obj_verbose_name}: {obj_description}")

    total_count = sum(len(objs) for model, objs in collector.model_objs.items())
    if total_count < 500:
        to_delete = collector.nested(format_callback)
    else:
        # Do not display a list of deleted items if there are too many.
        to_delete = []

    protected = [format_callback(obj) for obj in collector.protected]
    model_count = {}
    for model, objs in collector.model_objs.items():
        _related_obj, verbose_name, _object_description = get_related_obj_info(list(objs)[0])
        model_count[verbose_name] = len(objs)
    return to_delete, model_count, perms_needed, protected
