from django.urls import reverse, NoReverseMatch
from django.utils.html import format_html

from dbentry.utils import permission as perms

# TODO: add utils.admin.get_changelist_link and utils.admin.link_list


def urlname(name, opts=None, current_app=None):
    """
    Return the 'url name' for the given name/action.

    If model options ``opts`` is given, prepend app_label and model_name to
    the name:
        {opts.app_label}_{opts.model_name}_{name}
    If ``current_app`` is given, prepend the app namespace to the name:
        {current_app}:{name}
    """
    if opts:
        name = f"{opts.app_label}_{opts.model_name}_{name}"
    if current_app:
        return f"{current_app}:{name}"
    return name


def get_changelist_url(request, model, obj_list=None, current_app=None):
    """
    Return the URL for the changelist view of the given model.

    If ``obj_list``, a sequence of model objects, is given, then the url to the
    changelist will include a query parameter to filter to these objects.

    Return an empty string if the current user does not have 'view' (or 'change')
    permission.
    """
    opts = model._meta
    if not perms.has_view_permission(request.user, opts):
        return ''
    url = reverse(urlname('changelist', opts, current_app))

    if obj_list:
        url = f'{url}?id__in={",".join(str(obj.pk) for obj in obj_list)}'
    return url


def get_add_url(request, model, current_app=None):
    """
    Return the URL for the add view of the given model.

    Return an empty string if the current user does not have 'add' permission.
    """
    opts = model._meta
    if not perms.has_add_permission(request.user, opts):
        return ''
    return reverse(urlname('add', opts, current_app))


def get_change_url(request, obj, current_app=None):
    """
    Return the URL for the change view of the given model object.

    Return an empty string if the current user does not have 'change' permission.
    """
    opts = obj._meta
    if not perms.has_change_permission(request.user, opts):
        return ''
    return reverse(urlname('change', opts, current_app), args=[obj.pk])


def get_delete_url(request, obj, current_app=None):
    """
    Return the URL for the delete view of the given model object.

    Return an empty string if the current user does not have 'delete' permission.
    """
    opts = obj._meta
    if not perms.has_delete_permission(request.user, opts):
        return ''
    return reverse(urlname('delete', opts, current_app), args=[obj.pk])


def get_history_url(request, obj, current_app=None):
    """
    Return the URL for the history view of the given model object.

    Return an empty string if the current user does not have view (or change)
    permission.
    """
    opts = obj._meta
    if not perms.has_view_permission(request.user, opts):
        return ''
    return reverse(urlname('history', opts, current_app), args=[obj.pk])


def create_hyperlink(url, content, **attrs):
    """
    Return a safe string of an anchor element with its href attribute set to
    the given url.

    Args:
        url: the url of the link
        content: the text of the link
        **attrs: other element attributes (e.g. style or target)
    """
    _attrs = list(attrs.items())
    _attrs.insert(0, ('href', url))
    return format_html(
        '<a {attrs}>{content}</a>',
        attrs=format_html(' '.join(f'{k}="{v}"' for k, v in _attrs)),
        content=content
    )


def get_obj_link(request, obj, current_app=None, blank=False):
    """
    Return a safe link to the change page of the given model object.

    If no change page exists or the current user has no change permission, a
    simple string representation of ``obj`` is returned.
    If ``blank`` is True, the link will include a target="_blank" attribute.
    """
    try:
        url = get_change_url(request, obj, current_app)
    except NoReverseMatch:
        url = ""
    if not url:
        return format_html("{verbose_name}: {obj}", verbose_name=obj._meta.verbose_name, obj=obj)
    if blank:
        return create_hyperlink(url, obj, target='_blank')
    return create_hyperlink(url, obj)
