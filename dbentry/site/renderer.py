from django_bootstrap5.renderers import FieldRenderer
from mizdb_inlines.renderers import InlineFormsetRenderer, InlineFormRenderer

IS_INVALID_CLASS = "is-invalid"


class MIZFieldRenderer(FieldRenderer):

    def get_server_side_validation_classes(self):
        """Return CSS classes for server-side validation."""
        if self.field_errors:
            return IS_INVALID_CLASS
        return ""  # Do not add the 'is-valid' class to valid elements


class TabularInlineFormRenderer(InlineFormRenderer):
    """Renderer for inline forms that renders all fields in a row."""

    def get_field_container_class(self):
        return "col fields-container row"


class TabularInlineFormsetRenderer(InlineFormsetRenderer):
    form_renderer = TabularInlineFormRenderer
