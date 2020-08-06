from django.template import Library

from django.utils.html import format_html
from django.contrib.admin.views.main import ORDER_VAR

register = Library()


@register.filter
def tabindex(bound_field, index):
    """
    Add a tabindex attribute to the widget for a bound field.

    Arguments:
        - bound_field: the django.forms.BoundField instance whose widget will
            get a tabindex attribute
        - index (int): the tabindex

    Credit for idea to: Gareth Reese (stackoverflow)
    """
    bound_field.field.widget.attrs['tabindex'] = index
    return bound_field


@register.simple_tag
def reset_ordering(cl):
    """Provide a link that resets the ordering of the changelist results."""
    template = '<span class="small quiet"><a href={url}>Sortierung zurücksetzen</a></span>'
    url = cl.get_query_string(new_params=None, remove=[ORDER_VAR])
    return format_html(template, url=url)
