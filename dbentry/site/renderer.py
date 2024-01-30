from django_bootstrap5.renderers import FieldRenderer
from mizdb_inlines.renderers import InlineFormsetRenderer, InlineFormRenderer

IS_INVALID_CLASS = "is-invalid"


class NoValidFieldRenderer(FieldRenderer):
    # A FieldRenderer that doesn't add the 'is-valid' class to valid elements.

    def get_server_side_validation_classes(self):
        """Return CSS classes for server-side validation."""
        if self.field_errors:
            return IS_INVALID_CLASS
        return ""


class MIZFieldRenderer(NoValidFieldRenderer):
    pass


class TabularInlineFormRenderer(InlineFormRenderer):
    """Renderer for inline forms that renders all fields in a row."""

    def get_field_container_class(self):
        return "col fields-container row"


class TabularInlineFormsetRenderer(InlineFormsetRenderer):
    form_renderer = TabularInlineFormRenderer
