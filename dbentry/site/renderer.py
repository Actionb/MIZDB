from django_bootstrap5.renderers import FieldRenderer

IS_INVALID_CLASS = "is-invalid"


class MIZFieldRenderer(FieldRenderer):
    def get_server_side_validation_classes(self):
        """Return CSS classes for server-side validation."""
        if self.field_errors:
            return IS_INVALID_CLASS
        return ""  # Do not add the 'is-valid' class to valid elements
