from django.urls import reverse, NoReverseMatch
from django.utils.text import capfirst

from dbentry.utils import permission as perms


# TODO: check if anything actually uses the get_x_url functions
#  all they do is include a permission check and it might be better to do that explicitly where needed anyway


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
    try:
        url = reverse(urlname('changelist', opts, namespace))
    except NoReverseMatch:
        return ''

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


def get_change_or_view_url(request, obj, namespace=""):
    """
    Return the URL for the change or view page (depending on permissions) of
    the given model object.

    Return an empty string if the current user does not 'change' or 'view'
    permission.
    """
    return get_change_url(request, obj, namespace) or get_view_url(request, obj, namespace) or ""


def get_change_url(request, obj, namespace=''):
    """
    Return the URL for the change view of the given model object.

    Return an empty string if the current user does not have 'change' permission.
    """
    opts = obj._meta
    if not perms.has_change_permission(request.user, opts):
        return ''
    return reverse(urlname('change', opts, namespace), args=[obj.pk])


def get_view_url(request, obj, namespace=""):
    """
    Return the URL for the 'view' page of the given model object.

    Return an empty string if the current user does not have 'view' permission.
    """
    opts = obj._meta
    if not perms.has_view_permission(request.user, opts):
        return ""
    return reverse(urlname("view", opts, namespace), args=[obj.pk])


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


def get_changelist_url_for_relation(rel, model, object_id, url_callback, labels=None):
    """
    Determine the URL of the changelist that is filtered to the related objects
    of the given object.

    Returns a 3-tuple of:
        - changelist URL (or None if no base URL could be found)
        - count of the number of related objects
        - an appropriate label for the relation to be used in a link

    Args:
        rel: the relation for which to create a URL for
        object_id: the primary key of the main object
        model: the model of the main object
        url_callback: a callable that takes the model of the related objects
          and returns the URL to the changelist of the related objects
        labels: an optional mapping of related model name to label for the link
    """
    query_model = rel.related_model
    query_field = rel.remote_field.name
    if rel.many_to_many and query_model == model._meta.model:
        # M2M relations are symmetric, but we wouldn't want to create
        # a changelist link that leads back to *this* model's changelist
        # (unless it's a self relation).
        query_model = rel.model
        query_field = rel.name

    try:
        changelist_url = f"{url_callback(query_model)}?{query_field}={object_id}"
    except NoReverseMatch:
        changelist_url = None

    count = query_model.objects.filter(**{query_field: object_id}).count()
    if labels and query_model._meta.model_name in labels:
        label = labels[query_model._meta.model_name]
    elif rel.related_name:
        label = " ".join(capfirst(s) for s in rel.related_name.split('_'))
    else:
        label = query_model._meta.verbose_name_plural
    return changelist_url, count, label
