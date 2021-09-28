from typing import Union

from django.contrib.admin.helpers import AdminField
from django.contrib.admin.views.main import ChangeList, ORDER_VAR
from django.forms import BoundField
from django.template.library import Library
from django.utils.html import format_html
from django.utils.safestring import SafeText

register = Library()


@register.filter
def tabindex(bound_field: BoundField, index: int) -> BoundField:
    """
    Add a tabindex attribute to the widget of a bound field.

    Credit for idea to: Gareth Reese (stackoverflow)

    Args:
        bound_field (BoundField): BoundField instance whose widget will get a
          tabindex attribute
        index (int): the tabindex

    Returns:
        BoundField: the updated BoundField instance
    """
    # FIXME: fix tabbing breaking when exiting a dal widget (focus being lost)
    # (probably requires javascript)
    bound_field.field.widget.attrs['tabindex'] = index
    return bound_field


@register.simple_tag
def reset_ordering(cl: ChangeList) -> Union[SafeText, str]:
    """Provide a link that resets the ordering of the changelist results."""
    if ORDER_VAR not in cl.params:
        return ''
    template = '<span class="small quiet"><a href={url}>Sortierung zurücksetzen</a></span>'
    url = cl.get_query_string(new_params=None, remove=[ORDER_VAR])
    return format_html(template, url=url)


@register.filter
def checkbox_label(admin_field: AdminField) -> str:
    """
    Provide label tag for a 'checkbox' AdminField in a django admin Fieldset.

    By default AdminField treats checkbox fields differently:
        - the label for an AdminField is to the right of the checkbox input
          (due to css class "vCheckboxLabel")
        - the label does not have a suffix (usually ":")

    This filter reverts that special treatment by setting is_checkbox to False.

    Args:
        admin_field: a django.contrib.admin.helpers.AdminField instance
    """
    admin_field.is_checkbox = False
    return admin_field.label_tag()
