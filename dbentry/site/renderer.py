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


class FixedFieldRenderer(FieldRenderer):
    """
    A field renderer that applies `field_class` argument to the element.

    Workaround for: https://github.com/zostera/django-bootstrap5/issues/287
    """

    # TODO: remove when the workaround is no longer needed

    def add_widget_class_attrs(self, widget=None):
        if widget is None:  # pragma: no cover
            widget = self.widget
        super().add_widget_class_attrs(widget)
        classes = widget.attrs.get("class", "")
        if self.field_class:
            classes += f" {self.field_class}"
        widget.attrs["class"] = classes


class MIZFieldRenderer(NoValidFieldRenderer, FixedFieldRenderer):
    pass


class TabularInlineFormRenderer(InlineFormRenderer):
    """Renderer for inline forms that renders all fields in a row."""

    def get_field_container_class(self):
        return "col fields-container row"


class TabularInlineFormsetRenderer(InlineFormsetRenderer):
    form_renderer = TabularInlineFormRenderer
