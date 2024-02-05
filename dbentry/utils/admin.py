from typing import Dict, Iterable, List, Optional, Sequence, Type, Union

from django.contrib.admin.models import ADDITION, CHANGE, DELETION, LogEntry
from django.contrib.admin.options import ModelAdmin, get_content_type_for_model
from django.contrib.admin.sites import AdminSite
from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename
from django.contrib.auth.models import User
from django.db.models import Model
from django.forms import BaseInlineFormSet, ModelForm
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.text import capfirst
from django.utils.translation import override as translation_override

from dbentry.utils.models import get_model_from_string


def get_change_page_url(obj: Model, user: User, site_name: str = 'admin') -> str:  # TODO: remove - unused
    """
    Return the URL to the change page of ``obj``.

    Returns an empty string if no change page could be found, or if the user
    has no change permissions.
    """
    opts = obj._meta
    try:
        admin_url = reverse(
            '%s:%s_%s_change' % (site_name, opts.app_label, opts.model_name),
            args=[quote(obj.pk)]
        )
    except NoReverseMatch:
        return ''

    perm = '%s.%s' % (opts.app_label, get_permission_codename('change', opts))
    if not user.has_perm(perm):
        return ''
    return admin_url


def get_changelist_url(
        model: Union[Model, Type[Model]],
        user: User,
        site_name: str = 'admin',
        obj_list: Optional[Iterable[Model]] = None
) -> str:  # TODO: remove - unused
    """
    Return an url to the changelist of ``model``.

    If ``obj_list`` is given, the url to the changelist will include a query
    parameter to filter to records in that list.

    Args:
        model (model class or instance): the model of the desired changelist
        user (User): the user that the URL is for
        site_name (str): namespace of the site/app
        obj_list (Iterable): an iterable of model instances. If given, the url
          to the changelist will include a query parameter to filter to records
          in that list.
    """
    # noinspection PyUnresolvedReferences
    opts = model._meta
    try:
        url = reverse(
            '%s:%s_%s_changelist' % (site_name, opts.app_label, opts.model_name)
        )
    except NoReverseMatch:
        return ''

    change_perm = '%s.%s' % (opts.app_label, get_permission_codename('change', opts))
    view_perm = '%s.%s' % (opts.app_label, get_permission_codename('view', opts))
    if not (user.has_perm(change_perm) or user.has_perm(view_perm)):
        # 'change' or 'view' permission is required to access the changelist.
        return ''

    if obj_list:
        url += '?id__in={}'.format(",".join([str(obj.pk) for obj in obj_list]))
    return url


def get_model_admin_for_model(
        model: Union[Type[Model], str], *admin_sites: AdminSite
) -> Optional[ModelAdmin]:
    """
    Check the registries of ``admin_sites`` for a ModelAdmin that represents
    ``model`` and return the first such ModelAdmin instance found.
    """
    from dbentry.sites import miz_site
    if isinstance(model, str):
        model = get_model_from_string(model)  # type: ignore[assignment]
    sites = admin_sites or [miz_site]
    for site in sites:
        if site.is_registered(model):
            return site._registry.get(model)
    return None


def construct_change_message(
        form: ModelForm, formsets: List[BaseInlineFormSet], add: bool
) -> List[Dict]:
    """
    Construct a JSON structure describing changes from a changed object.

    Translations are deactivated so that strings are stored untranslated.
    Translation happens later on LogEntry access.
    """
    change_message: List[Dict] = []
    if add:
        change_message.append({'added': {}})
    elif form.changed_data:
        changed_fields = [form.fields[field].label for field in form.changed_data]
        change_message.append({'changed': {'fields': changed_fields}})
    # Handle relational changes:
    if formsets:
        parent_model = form._meta.model
        with translation_override(None):
            for formset in formsets:
                for added_object in formset.new_objects:
                    msg = _get_relation_change_message(added_object, parent_model)
                    change_message.append({'added': msg})
                for changed_object, changed_fields in formset.changed_objects:
                    msg = _get_relation_change_message(changed_object, parent_model)
                    msg['fields'] = changed_fields
                    change_message.append({'changed': msg})
                for deleted_object in formset.deleted_objects:
                    msg = _get_relation_change_message(deleted_object, parent_model)
                    change_message.append({'deleted': msg})
    return change_message


def _get_relation_change_message(obj: Model, parent_model: Type[Model]) -> Dict:
    """
    Create the change message JSON for changes on m2m and m2o relations.

    Args:
        obj (model instance): the related model instance
        parent_model (model class): the model class that 'obj' is related to
    """
    # The related models are responsible for creating useful textual
    # representations of themselves and their instances.
    # Exempt from this are auto created models such as the through tables of m2m
    # relations. Use the textual representation provided by the model on the
    # other end of the m2m relation instead.
    # noinspection PyUnresolvedReferences
    opts = obj._meta
    if opts.auto_created:
        # Follow the relation to the model that isn't the parent model.
        if issubclass(parent_model, opts.auto_created):
            # parent_model inherited this relation from opts.auto_created.
            parent_model = opts.auto_created
        for fld in opts.get_fields():
            if fld.is_relation and fld.related_model != parent_model:
                return {
                    # Use the verbose_name of the model on the other end of the
                    # m2m relation as 'name'.
                    'name': str(fld.related_model._meta.verbose_name),
                    # Use the other related object directly instead of the
                    # record in the auto created through table.
                    'object': str(getattr(obj, fld.name))
                }
    return {
        'name': str(opts.verbose_name),
        'object': str(obj),
    }


def create_logentry(
        user_id: int,
        obj: Model,
        action_flag: int,
        message: Union[str, list] = ''
) -> LogEntry:
    """
    Create a LogEntry object to log an action.

    Args:
        user_id (int): the id of the user that made the action
        obj (model instance): the model instance that the action affected
        action_flag (int): the integer flag/representation of the action
        message (str or list): the change message to add to the LogEntry
    """
    return LogEntry.objects.log_action(  # pragma: no cover
        user_id=user_id,
        content_type_id=get_content_type_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=message,
    )


def log_addition(user_id: int, obj: Model, related_obj: Model = None) -> LogEntry:
    """
    Log that an object has been successfully added.

    If ``related_obj`` is given, log that a related object has been added to
    ``object``.
    """
    message: Dict[str, dict] = {"added": {}}
    if related_obj:
        # noinspection PyUnresolvedReferences
        message['added'] = _get_relation_change_message(
            related_obj, obj._meta.model
        )
    return create_logentry(user_id, obj, ADDITION, [message])


def log_change(
        user_id: int,
        obj: Model,
        fields: Union[Sequence[str], str],
        related_obj: Model = None
) -> LogEntry:
    """
    Log that values for the ``fields`` of ``object`` have changed.

    If ``related_obj`` is given, log that a related object's field values have
    been changed. (useful for logging changes made with admin inlines)
    """
    if isinstance(fields, str):  # pragma: no cover
        fields = [fields]
    message: Dict[str, dict] = {'changed': {}}
    # noinspection PyUnresolvedReferences
    opts = obj._meta
    if related_obj:
        message['changed'] = _get_relation_change_message(
            related_obj, opts.model
        )
        # Use the fields map of the related model:
        # noinspection PyUnresolvedReferences
        opts = related_obj._meta

    # noinspection PyTypeChecker
    message['changed']['fields'] = sorted(
        capfirst(opts.get_field(f).verbose_name) for f in fields
    )
    return create_logentry(user_id, obj, CHANGE, [message])


def log_deletion(user_id: int, obj: Model) -> LogEntry:
    """Log that an object will be deleted."""
    return create_logentry(user_id, obj, DELETION)
