from typing import Union

from django.contrib.admin.helpers import AdminField
from django.contrib.admin.views.main import ORDER_VAR, ChangeList
from django.template.library import Library
from django.utils.html import format_html
from django.utils.safestring import SafeText

register = Library()


@register.simple_tag
def reset_ordering(cl: ChangeList) -> Union[SafeText, str]:
    """Provide a link that resets the ordering of the changelist results."""
    if ORDER_VAR not in cl.params:
        return ""
    template = '<span class="small quiet"><a href={url}>Sortierung zurücksetzen</a></span>'
    url = cl.get_query_string(new_params=None, remove=[ORDER_VAR])
    return format_html(template, url=url)


@register.filter
def checkbox_label(admin_field: AdminField) -> str:
    """
    Provide label tag for a 'checkbox' AdminField in a django admin Fieldset.

    By default, AdminField treats checkbox fields differently than other fields:
        - the label for an AdminField is to the right of the checkbox input
          (due to css class "vCheckboxLabel")
        - the label does not have a suffix (usually ":")

    This filter reverts that special treatment by setting is_checkbox to False.

    Args:
        admin_field: a django.contrib.admin.helpers.AdminField instance
    """
    admin_field.is_checkbox = False
    return admin_field.label_tag()
