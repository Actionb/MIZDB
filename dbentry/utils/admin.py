from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.admin.options import get_content_type_for_model
from django.contrib.admin.utils import quote
from django.contrib.auth import get_permission_codename
from django.urls import reverse, NoReverseMatch
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.text import capfirst
from django.utils.translation import override as translation_override

from dbentry.utils.models import get_model_from_string


def create_hyperlink(url, content, **attrs):
    """Return a safe <a> element."""
    attrs = list(attrs.items())
    attrs.insert(0, ('href', url))
    return format_html(
        '<a {attrs}>{content}</a>',
        attrs=format_html(' '.join('{}="{}"'.format(k, v) for k, v in attrs)),
        content=content
    )


def get_obj_link(obj, user, site_name='admin', blank=False):
    """
    Return a safe link to the change page of 'obj'.

    If no change page exists or the user has no change permission,
    A simple string representation of 'obj' is returned.
    If 'blank' is True, the link will include a target="_blank" attribute.
    """
    opts = obj._meta
    no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), force_text(obj))
    try:
        admin_url = reverse(
            '%s:%s_%s_change' % (site_name, opts.app_label, opts.model_name),
            args=[quote(obj.pk)]
        )
    except NoReverseMatch:
        return no_edit_link

    perm = '%s.%s' % (opts.app_label, get_permission_codename('change', opts))
    if not user.has_perm(perm):
        return no_edit_link

    if blank:
        return create_hyperlink(admin_url, obj, target='_blank')
    return create_hyperlink(admin_url, obj)


def get_changelist_url(model, user, site_name='admin', obj_list=None):
    """
    Return an url to the changelist of 'model'.

    If 'obj_list' is given, the url to the changelist will include a query
    param to filter to records in that list.
    """
    opts = model._meta
    try:
        url = reverse(
            '%s:%s_%s_changelist' % (site_name, opts.app_label, opts.model_name))
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


def get_changelist_link(
        model, user, site_name='admin', obj_list=None, content='Liste', blank=False):
    """
    Return a safe link to the changelist of 'model'.

    Optional arguments:
        - site_name (default 'admin'): namespace of the site/app
        - obj_list: an iterable of model instances
            if given, the changelist will only include those instances
        - content: string for the 'content' between the <a> tags
        - blank: if True, the link will include a target="_blank" attribute
    """
    url = get_changelist_url(
        model, user, site_name=site_name, obj_list=obj_list
    )
    if blank:
        return create_hyperlink(url, content, target='_blank')
    return create_hyperlink(url, content)


def link_list(request, obj_list, sep=", ", blank=False):
    """
    Return links to the change page of each object in 'obj_list', separated by
    'sep'.
    If 'blank' is True, the links will include a target="_blank" attribute.
    """
    links = []
    for obj in obj_list:
        links.append(get_obj_link(obj, request.user, blank=blank))
    return format_html(sep.join(links))


def get_model_admin_for_model(model, *admin_sites):
    """
    Check the registries of 'admin_sites' for a ModelAdmin that represents
    'model' and return the first ModelAdmin found.
    """
    from dbentry.sites import miz_site
    if isinstance(model, str):
        model = get_model_from_string(model)
    sites = admin_sites or [miz_site]
    for site in sites:
        if site.is_registered(model):
            return site._registry.get(model)
    return None


def has_admin_permission(request, model_admin):
    """Return True if the user has either any module or model permissions."""
    # (used by help views)
    # Check if the user has any permissions to the module/app.
    if not model_admin.has_module_permission(request):
        return False
    # Check if the user has any permissions
    # (add, change, delete, view) for the model.
    return True in model_admin.get_model_perms(request).values()


def construct_change_message(form, formsets, add):
    """
    Construct a JSON structure describing changes from a changed object.

    Translations are deactivated so that strings are stored untranslated.
    Translation happens later on LogEntry access.
    """
    change_message = []
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


def _get_relation_change_message(obj, parent_model):
    """
    Create the change message JSON for changes on relations.

    Arguments:
        - obj (model instance): the related model instance
        - parent_model (model class): the model class that 'obj' is related to
    """
    # The related models are responsible for creating useful textual
    # representations of themselves and their instances.
    # Exempt from this are auto created models such as the through tables of m2m
    # relations. Use the textual representation provided by the model on the
    # other end of the m2m relation instead.
    result = {
        'name': str(obj._meta.verbose_name),
        'object': str(obj),
    }
    if obj._meta.auto_created:
        # An auto_created m2m through table only has two relation fields;
        # one is the field pointing towards the parent model and the other is
        # the one we are looking for here.
        for fld in obj._meta.get_fields():
            if fld.is_relation and fld.related_model != parent_model:
                # Use the verbose_name of the model on the other end of the m2m
                # relation as 'name'.
                result['name'] = str(fld.related_model._meta.verbose_name)
                # Use the other related object directly instead of the record
                # in the auto created through table.
                result['object'] = str(getattr(obj, fld.name))
                break
    return result


def create_logentry(user_id, obj, action_flag, message=''):
    return LogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=get_content_type_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=str(obj),
        action_flag=action_flag,
        change_message=message,
    )


def log_addition(user_id, obj, related_obj=None):
    """
    Log that an object has been successfully added.

    If 'related_obj' is given, log that a related object has been added to
    'object'.
    """
    message = {"added": {}}
    if related_obj:
        message['added'] = {
            'name': str(related_obj._meta.verbose_name),
            'object': str(related_obj),
        }
    return create_logentry(user_id, obj, ADDITION, [message])


def log_change(user_id, obj, fields, related_obj=None):
    """
    Log that values for the fields 'fields' of object 'object' have changed.

    If 'related_obj' is given, log that a related object's field values have
    been changed.
    """
    if isinstance(fields, str):
        fields = [fields]
    message = {'changed': {}}
    if related_obj:
        message['changed'] = _get_relation_change_message(related_obj, obj)
        # Use the fields map of the related model:
        fields_opts = related_obj._meta
    else:
        fields_opts = obj._meta

    message['changed']['fields'] = sorted(
        capfirst(fields_opts.get_field(f).verbose_name) for f in fields)
    return create_logentry(user_id, obj, CHANGE, [message])


def log_deletion(user_id, obj):
    """Log that an object will be deleted."""
    return create_logentry(user_id, obj, DELETION)
