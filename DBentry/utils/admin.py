from django.contrib.auth import get_permission_codename
from django.contrib.admin.utils import quote
from django.core import exceptions
from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html
from django.utils.encoding import force_text
from django.utils.text import capfirst

from DBentry.utils.models import get_model_from_string


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

    perm = '%s.%s' % (opts.app_label,get_permission_codename('change', opts))
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

    perm = '%s.%s' % (opts.app_label, get_permission_codename('changelist', opts))
    if not user.has_perm(perm):
        return ''

    if obj_list:
        url += '?id={}'.format(",".join([str(obj.pk) for obj in obj_list]))
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


def resolve_list_display_item(model_admin, item):
    """
    A ModelAdmin's list_display may contain any of the following:
        - name of a model field
        - callable
        - name of a method of model_admin
        - name of a method or attribute of model_admin.model
    This helper function takes an item of list_display and returns the first
    object that matches any of the possiblities given above
    (or None if no match).
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
