from operator import itemgetter
from typing import Any

from django import forms
from django.contrib.admin.helpers import Fieldset
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.validators import MinValueValidator
from django.urls import reverse_lazy

from dbentry import models as _models
from dbentry.admin.forms import MIZAdminForm
from dbentry.base.forms import DynamicChoiceFormMixin
from dbentry.query import InvalidJahrgangError


class BulkEditJahrgangForm(DynamicChoiceFormMixin, MIZAdminForm):
    """
    The form to edit the Jahrgang value for a collection of Ausgabe instances.

    Fields:
        - ``start`` (ChoiceField): the Ausgabe instance from which to count up
          the jahrgang values
        - ``jahrgang`` (IntegerField): the jahrgang value for the starting
          instance
    """

    start = forms.ChoiceField(
        required=True,
        choices=(),
        label="Schlüssel-Ausgabe",
        help_text="Wählen Sie eine Ausgabe.",
        widget=forms.RadioSelect(),
    )
    jahrgang = forms.IntegerField(
        required=True,
        help_text="Geben Sie den Jahrgang für die oben ausgewählte Ausgabe an.",
        validators=[MinValueValidator(limit_value=0)],
    )

    def clean(self):
        cleaned_data = super().clean()
        start_id = cleaned_data.get("start")
        jahrgang = cleaned_data.get("jahrgang")
        if start_id and jahrgang:
            pks = list(map(itemgetter(0), self.fields["start"].choices))
            queryset = _models.Ausgabe.objects.filter(id__in=pks)
            start_obj = _models.Ausgabe.objects.get(pk=start_id)
            try:
                # Run increment_jahrgang, without committing anything, to see
                # if the jahrgang values are valid for all objects.
                queryset.increment_jahrgang(start_obj=start_obj, start_jg=jahrgang, commit=False)
            except InvalidJahrgangError:
                self.add_error("jahrgang", "Der Jahrgang ist für mind. eine Ausgabe ungültig (Wert wäre kleiner 1).")
        return cleaned_data


class MergeFormSelectPrimary(DynamicChoiceFormMixin, forms.Form):
    """
    A form that lets the user select the 'primary' object when merging objects.

    Fields:
        - ``primary`` (ChoiceField): the object that other objects
          will be merged into.
        - ``expand_primary`` (BooleanField): whether to expand the primary
          object with data from the other objects.
    """

    primary = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.HiddenInput(),
        label=(
            "Bitten wählen Sie den Datensatz, dem die verwandten Objekte der "
            "anderen Datensätze angehängt werden sollen"
        ),
    )
    expand_primary = forms.BooleanField(
        required=False,
        label="Primären Datensatz erweitern",
        initial=True,
        help_text=(
            "Sollen fehlende Grunddaten des primäre Datensatzes um in anderen "
            "Datensätzen vorhandenen Daten erweitert werden?"
        ),
    )

    PRIMARY_FIELD_NAME = "primary"
    required_css_class = "required"

    class Media:
        css = {"all": ("admin/css/changelists.css",)}

    def expand_primary_fieldset(self) -> Fieldset:
        """Provide a Fieldset object of the expand_primary field for the template."""
        return Fieldset(self, fields=["expand_primary"])


class MergeFormHandleConflicts(DynamicChoiceFormMixin, forms.Form):
    """
    The form that resolves merge conflicts for one model field.

    Fields:
        - ``original_fld_name`` (HiddenInput): stores the name of the field
        - ``verbose_fld_name`` (HiddenInput): stores the verbose name of the
          field
        - ``posvals`` (ChoiceField): the different possible values for this
          model field
    """

    original_fld_name = forms.CharField(required=False, widget=forms.HiddenInput())
    verbose_fld_name = forms.CharField(required=False, widget=forms.HiddenInput())
    posvals = forms.ChoiceField(choices=[], label="Mögliche Werte", widget=forms.RadioSelect())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Try to add a more accurate label to the posvals field.
        if self.initial.get("verbose_fld_name"):
            self.fields["posvals"].label = f"Mögliche Werte für Feld {self.initial['verbose_fld_name']}:"


class AdminMergeFormHandleConflicts(MergeFormHandleConflicts, MIZAdminForm):
    pass


# To handle merge conflicts for multiple fields, use these formset:
MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, extra=0, can_delete=False)
AdminMergeConflictsFormSet = forms.formset_factory(AdminMergeFormHandleConflicts, extra=0, can_delete=False)


class BrochureActionForm(MIZAdminForm):
    """
    The form to move an Ausgabe instance to any of the Brochure models.

    Fields:
        - ``ausgabe_id`` (HiddenInput): id of the Ausgabe instance
        - ``titel`` (CharField): value for the titel model field of a Brochure
        - ``beschreibung`` (CharField): value for the beschreibung field
        - ``bemerkungen`` (CharField): value for the bemerkungen field
        - ``zusammenfassung`` (CharField): value for the zusammenfassung field
        - ``accept`` (BooleanField): confirm the changes for this instance
    """

    textarea_config = {"rows": 2, "cols": 90}

    ausgabe_id = forms.IntegerField(widget=forms.HiddenInput())
    titel = forms.CharField(widget=forms.Textarea(attrs=textarea_config))
    beschreibung = forms.CharField(widget=forms.Textarea(attrs=textarea_config), required=False)
    bemerkungen = forms.CharField(widget=forms.Textarea(attrs=textarea_config), required=False)
    zusammenfassung = forms.CharField(widget=forms.Textarea(attrs=textarea_config), required=False)
    accept = forms.BooleanField(
        label="Änderungen bestätigen",
        required=False,
        initial=True,
        help_text=(
            "Hiermit bestätigen Sie, dass diese Ausgabe verschoben werden soll. "
            "Entfernen Sie das Häkchen, um diese Ausgabe zu überspringen und "
            "nicht zu verschieben."
        ),
    )

    fieldsets = [
        (None, {"fields": ["ausgabe_id", ("titel", "zusammenfassung"), ("beschreibung", "bemerkungen"), "accept"]})
    ]


BrochureActionFormSet = forms.formset_factory(
    form=BrochureActionForm, formset=forms.BaseFormSet, extra=0, can_delete=True
)


class BrochureActionFormOptions(MIZAdminForm):
    """
    The form that displays additional options for moving Ausgaben to Brochure.

    Fields:
        - ``brochure_art`` (ChoiceField): select the subtype of brochure to
          move the Ausgabe instances to
        - ``delete_magazin`` (BooleanField): whether to delete the magazin the
          Ausgabe instances belong to after moving.
    """

    # noinspection PyUnresolvedReferences
    brochure_art = forms.ChoiceField(
        label="Verschieben nach",
        choices=[
            (_models.Brochure._meta.model_name, _models.Brochure._meta.verbose_name),
            (_models.Katalog._meta.model_name, _models.Katalog._meta.verbose_name),
            (_models.Kalender._meta.model_name, _models.Kalender._meta.verbose_name),
        ],
    )

    delete_magazin = forms.BooleanField(
        label="Magazin löschen",
        required=False,
        help_text="Soll das Magazin dieser Ausgaben anschließend gelöscht werden?",
    )

    def __init__(self, can_delete_magazin: bool = True, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["delete_magazin"].disabled = not can_delete_magazin


class ReplaceForm(DynamicChoiceFormMixin, MIZAdminForm):
    """Form for selecting the model objects that should replace another object."""

    replacements = forms.MultipleChoiceField(
        label="Ersetzen durch:",
        widget=FilteredSelectMultiple("Datensätze", False),
        choices=[],
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        model = kwargs["choices"]["replacements"].model
        self.fields["replacements"].widget.verbose_name = model._meta.verbose_name_plural

    class Media:
        # FilteredSelectMultiple requires jsi18n:
        js = [reverse_lazy("admin:jsi18n")]
