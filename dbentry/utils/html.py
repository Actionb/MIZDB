from django.urls import NoReverseMatch
from django.utils.html import format_html

from dbentry.utils.url import get_change_url


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


def get_obj_link(request, obj, namespace='', blank=False):
    """
    Return a safe link to the change page of the given model object.

    If no change page exists or the current user has no change permission, a
    simple string representation of ``obj`` is returned.
    If ``blank`` is True, the link will include a target="_blank" attribute.
    """
    try:
        url = get_change_url(request, obj, namespace)
    except NoReverseMatch:
        url = ""
    if not url:
        return format_html("{verbose_name}: {obj}", verbose_name=obj._meta.verbose_name, obj=obj)
    if blank:
        return create_hyperlink(url, obj, target='_blank')
    return create_hyperlink(url, obj)
