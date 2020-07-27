from django.contrib.auth import get_permission_codename
from django.contrib.admin.utils import quote
from django.core import exceptions
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.text import capfirst

from DBentry.utils.models import get_model_from_string


def get_obj_link(obj, user, site_name='admin', include_name=True):
    """
    Return a safe link to the change page of 'obj'.

    If include_name is True, the verbose_name of the obj's model is prepended
    to the link.
    If no change page exists or the user has no change permission,
    A simple string representation of 'obj' is returned.
    """
    opts = obj._meta
    no_edit_link = '%s: %s' % (capfirst(opts.verbose_name), force_text(obj))
    try:
        viewname = '%s:%s_%s_change' % (
            site_name,
            opts.app_label,
            opts.model_name
        )
        admin_url = reverse(viewname, args=[quote(obj.pk)])
    except NoReverseMatch:
        return no_edit_link

    perm = '%s.%s' % (
        opts.app_label,
        get_permission_codename('change', opts)
    )
    if not user.has_perm(perm):
        return no_edit_link

    if include_name:
        return format_html(
            '{}: <a href="{}">{}</a>',
            capfirst(opts.verbose_name),
            admin_url,
            obj
        )
    return format_html('<a href="{}">{}</a>', admin_url, obj)


def get_changelist_url(model, user, site_name='admin', obj_list=None):
    """
    Return an url to the changelist of 'model'.

    If 'obj_list' is given, the url to the changelist will include a query
    param to filter to records in that list.
    """
    opts = model._meta
    try:
        url = reverse(
            '%s:%s_%s_changelist' % (site_name, opts.app_label, opts.model_name)
        )
    except NoReverseMatch:
        return ''
    perm = '%s.%s' % (
        opts.app_label,
        get_permission_codename('changelist', opts)
    )
    if not user.has_perm(perm):
        return ''
    if obj_list:
        url += '?id={}'.format(",".join([str(obj.pk) for obj in obj_list]))
    return url


def get_changelist_link(model, user, site_name='admin', obj_list=None):
    """
    Return a safe link to the changelist of 'model'.

    If 'obj_list' is given, the url to the changelist will include a query
    param to filter to records in that list.
    """
    return format_html(
        '<a href="{}">Liste</a>',
        get_changelist_url(
            model, user, site_name='admin', obj_list=obj_list
        )
    )


def link_list(request, obj_list, sep=", "):
    """
    Return links to the change page of each object in 'obj_list', separated by 'sep'.
    """
    links = []
    for obj in obj_list:
        links.append(get_obj_link(obj, request.user, include_name=False))
    return format_html(sep.join(links))


def get_model_admin_for_model(model, *admin_sites):
    """
    Check the registries of 'admin_sites' for a ModelAdmin that represents 'model'.
    Return the first ModelAdmin found.
    """
    from DBentry.sites import miz_site
    if isinstance(model, str):
        model = get_model_from_string(model)
    sites = admin_sites or [miz_site]
    for site in sites:
        if site.is_registered(model):
            return site._registry.get(model)


def has_admin_permission(request, model_admin):
    """Return True if the user has either any module or model permissions."""
    # (used by help views)
    # Check if the user has any permissions to the module/app.
    if not model_admin.has_module_permission(request):
        return False
    # Check if the user has any permissions
    # (add, change, delete, view) for the model.
    return True in model_admin.get_model_perms(request).values()


def make_simple_link(url, label, is_popup, as_listitem=False):
    """
    Return a safe link to 'url'.

    If is_popup is True, the link will include an 'onclick' attribute that calls
    'popup(this)'.
    If as_listitem is True, the link is wrapped in <li> tags.
    """
    if is_popup:
        # FIXME: Does return popup(this) actually do ANYTHING?
        template = '<a href="{url}?_popup=1" onclick="return popup(this)">{label}</a>'
    else:
        template = '<a href="{url}" target="_blank">{label}</a>'
    if as_listitem:
        template = '<li>' + template + '</li>'
    return format_html(template, url=url, label=label)


def resolve_list_display_item(model_admin, item):
    """
    A ModelAdmin's list_display may contain any of the following:
        name of a model field
        callable
        name of a method of model_admin
        name of a method or attribute of model_admin.model
    This helper function takes an item of list_display and returns the first
    object that matches any of the possiblities given above (or None if no match).
    """
    # (used in base.admin as a helper to annotate sortable list_display items)
    try:
        return model_admin.opts.get_field(item)
    except exceptions.FieldDoesNotExist:
        if callable(item):
            func = item
        elif hasattr(model_admin, item) and item != '__str__':
            # item is a method of model_admin. '__str__' would refer to the
            # model's str() method - NOT the ModelAdmin's.
            func = getattr(model_admin, item)
        elif hasattr(model_admin.model, item):
            func = getattr(model_admin.model, item)
        else:
            func = None
    return func
