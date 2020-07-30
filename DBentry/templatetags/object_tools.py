from django.urls import reverse, exceptions
from django.template import Library

from DBentry.utils import make_simple_link

register = Library()


@register.simple_tag(takes_context=True)
def favorites_link(context):
    """Return a link to the 'favorites' view."""
    try:
        url = reverse('favoriten')
    except exceptions.NoReverseMatch:
        return ''
    return make_simple_link(
        url=url,
        label='Favoriten',
        is_popup=context.get('is_popup', False),
        as_listitem=True
    )
