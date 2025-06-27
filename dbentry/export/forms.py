from django import forms
from import_export.forms import ExportForm

from dbentry.base.forms import DynamicChoiceFormMixin


class MIZSelectableFieldsExportForm(DynamicChoiceFormMixin, ExportForm):
    fields_select = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple,
        label="Felder auswählen",
        help_text="Bitte wählen Sie die Felder aus, die exportiert werden sollen",
    )
    format = forms.ChoiceField(label="Dateiformat", help_text="Bitte wählen Sie das Dateiformat")

    field_order = ["fields_select", "format"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initially, render each checkbox as checked:
        self.fields["fields_select"].initial = [c[0] for c in self.fields["fields_select"].choices]
