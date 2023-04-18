from django.urls import reverse

from dbentry.utils import permission as perms


# TODO: add utils.admin.get_changelist_link and utils.admin.link_list


def urlname(name, opts=None, namespace=''):
    """
    Return the 'url name' for the given name/action.

    If model options ``opts`` is given, prepend app_label and model_name to
    the name:
        {opts.app_label}_{opts.model_name}_{name}
    If ``namespace`` is given, prepend the namespace to the name:
        {namespace}:{name}
    """
    if opts:
        name = f"{opts.app_label}_{opts.model_name}_{name}"
    if namespace:
        return f"{namespace}:{name}"
    return name


def get_changelist_url(request, model, obj_list=None, namespace=''):
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
    url = reverse(urlname('changelist', opts, namespace))

    if obj_list:
        url = f'{url}?id__in={",".join(str(obj.pk) for obj in obj_list)}'
    return url


def get_add_url(request, model, namespace=''):
    """
    Return the URL for the add view of the given model.

    Return an empty string if the current user does not have 'add' permission.
    """
    opts = model._meta
    if not perms.has_add_permission(request.user, opts):
        return ''
    return reverse(urlname('add', opts, namespace))


def get_change_url(request, obj, namespace=''):
    """
    Return the URL for the change view of the given model object.

    Return an empty string if the current user does not have 'change' permission.
    """
    opts = obj._meta
    if not perms.has_change_permission(request.user, opts):
        return ''
    return reverse(urlname('change', opts, namespace), args=[obj.pk])


def get_delete_url(request, obj, namespace=''):
    """
    Return the URL for the delete view of the given model object.

    Return an empty string if the current user does not have 'delete' permission.
    """
    opts = obj._meta
    if not perms.has_delete_permission(request.user, opts):
        return ''
    return reverse(urlname('delete', opts, namespace), args=[obj.pk])


def get_history_url(request, obj, namespace=''):
    """
    Return the URL for the history view of the given model object.

    Return an empty string if the current user does not have view (or change)
    permission.
    """
    opts = obj._meta
    if not perms.has_view_permission(request.user, opts):
        return ''
    return reverse(urlname('history', opts, namespace), args=[obj.pk])
