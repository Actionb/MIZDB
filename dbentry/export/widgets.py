from import_export.widgets import BooleanWidget


class YesNoBooleanWidget(BooleanWidget):

    def render(self, value, obj=None):
        if value in self.NULL_VALUES:
            return ""
        return "Ja" if value else "Nein"
