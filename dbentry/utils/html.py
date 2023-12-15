from typing import Union, Type, Optional, Iterable, Any

from django.db.models import Model
from django.http import HttpRequest
from django.urls import NoReverseMatch
from django.utils.html import format_html
from django.utils.safestring import SafeText

from dbentry.utils.url import get_change_url, get_changelist_url, get_view_url


def create_hyperlink(url: str, content: str, **attrs: Any) -> SafeText:
    """
    Return a safe string of an anchor element with its href attribute set to
    the given url.

    Args:
        url: the url of the link
        content: the text of the link
        **attrs: other element attributes (e.g. style or target)
    """
    _attrs = list(attrs.items())
    _attrs.insert(0, ("href", url))
    return format_html(
        "<a {attrs}>{content}</a>",
        attrs=format_html(" ".join(f'{k}="{v}"' for k, v in _attrs)),
        content=content,
    )


def _get_link_for_object(
    url_func: callable, request: HttpRequest, obj: Model, namespace: str = "", blank: bool = False
) -> Union[SafeText, str]:
    """
    Return a hyperlink for the URL returned by the url_func. Used by the
    `get_x_link` functions below.
    """
    try:
        url = url_func(request, obj, namespace)
    except NoReverseMatch:
        url = ""
    if not url:
        return str(obj)
    if blank:
        return create_hyperlink(url, str(obj), target="_blank")
    return create_hyperlink(url, str(obj))


def get_obj_link(request: HttpRequest, obj: Model, namespace: str = "", blank: bool = False) -> SafeText:
    """
    Return a safe link to the change page of the given model object.

    If no change page exists or the current user has no change permission, a
    simple string representation of ``obj`` is returned.

    If ``blank`` is True, the link will include a target="_blank" attribute.
    """
    return _get_link_for_object(get_change_url, request, obj, namespace, blank)


def get_view_link(request: HttpRequest, obj: Model, namespace: str = "", blank: bool = False) -> SafeText:
    """
    Return a safe link to the 'view' page of the given model object.

    If no view page exists or if the user has no view permission, return a
    string representation of the object.

    If ``blank`` is True, the link will include a target="_blank" attribute.
    """
    return _get_link_for_object(get_view_url, request, obj, namespace, blank)


def get_changelist_link(
        request: HttpRequest,
        model: Union[Model, Type[Model]],
        obj_list: Optional[Iterable[Model]] = None,
        content: str = 'Liste',
        namespace: str = '',
        blank: bool = False
) -> SafeText:
    """
    Return a safe link to the changelist of ``model``.

    If ``obj_list`` is given, the url to the changelist will include a query
    parameter to filter to records in that list.

    Args:
        request (HttpRequest): the current request
        model (model class or instance): the model of the desired changelist
        obj_list (Iterable): an iterable of model instances. If given, the url
          to the changelist will include a query parameter to filter to records
          in that list.
        content (str): the text of the link
        namespace (str): namespace of the site/app
        blank (bool): if True, the link will have a target="_blank" attribute
    """
    url = get_changelist_url(request, model, obj_list=obj_list, namespace=namespace)
    if blank:
        return create_hyperlink(url, content, target="_blank")
    return create_hyperlink(url, content)


def link_list(
        request: HttpRequest,
        obj_list: Iterable[Model],
        sep: str = ", ",
        namespace: str = '',
        blank: bool = False
) -> SafeText:
    """
    Return links to the change page of each object in ``obj_list``.

    Args:
        request (HttpRequest): the current request
        obj_list (Iterable): an iterable of the model instances
        sep (str): the string used to separate the links
        namespace (str): namespace of the site/app
        blank (bool): if True, the links will have a target="_blank" attribute
    """
    links = []
    for obj in obj_list:
        links.append(get_obj_link(request, obj, namespace=namespace, blank=blank))
    return format_html(sep.join(links))
