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
    # FIXME: fix tabbing breaking when exiting a dal widget (focus being lost)
    # (probably requires javascript)
    bound_field.field.widget.attrs['tabindex'] = index
    return bound_field


@register.simple_tag
def reset_ordering(cl):
    """Provide a link that resets the ordering of the changelist results."""
    if not ORDER_VAR in cl.params:
        return ''
    template = '<span class="small quiet"><a href={url}>Sortierung zurücksetzen</a></span>'
    url = cl.get_query_string(new_params=None, remove=[ORDER_VAR])
    return format_html(template, url=url)


@register.filter
def checkbox_label(admin_field):
    """
    Provide label tag for a 'checkbox' AdminField in a django admin Fieldset.

    Argument:
        - admin_field: a django.contrib.admin.helpers.AdminField instance

    By default AdminField treats checkbox fields differently:
        - the label for an AdminField is to the right of the checkbox input
            (due to css class "vCheckboxLabel")
        - the label does not have a suffix (usually ":")
    This filter reverts that special treatment.
    """
    admin_field.is_checkbox = False
    return admin_field.label_tag()
