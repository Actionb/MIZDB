from import_export.widgets import BooleanWidget, CharWidget


class YesNoBooleanWidget(BooleanWidget):
    def render(self, value, obj=None):
        if value in self.NULL_VALUES:
            return ""
        return "Ja" if value else "Nein"


class ChoiceLabelWidget(CharWidget):
    """A widget that exports the human-readable label of the selected choice."""

    def __init__(self, field_name):
        self.field_name = field_name
        super().__init__()

    def render(self, value, obj=None):
        # Use get_FOO_display method to get the human-readable labels:
        # https://docs.djangoproject.com/en/5.0/ref/models/instances/#django.db.models.Model.get_FOO_display
        try:
            return getattr(obj, f"get_{self.field_name}_display")()
        except (AttributeError, TypeError):
            pass
        return super().render(value, obj=obj)
