from django import forms
from django.core.exceptions import ValidationError

from DBentry.ac.widgets import make_widget
from DBentry.base.forms import MIZAdminForm, DynamicChoiceFormMixin
from DBentry.models import lagerort
from DBentry.utils import get_model_from_string


class BulkEditJahrgangForm(DynamicChoiceFormMixin, MIZAdminForm):
    """
    The form to edit the 'jahrgang' value for a collection of ausgabe instances.

    Fields:
        start (ChoiceField): the ausgabe instance from which to count up the
            'jahrgang' values.
        jahrgang (IntegerField): the 'jahrgang' value for the starting instance.
    """

    start = forms.ChoiceField(
        required = True,
        choices = (),
        label = 'Schlüssel-Ausgabe',
        help_text = 'Wählen Sie eine Ausgabe.',
        widget = forms.RadioSelect(),
    )
    jahrgang = forms.IntegerField(
        required = True,
        help_text = 'Geben Sie den Jahrgang für die oben ausgewählte Ausgabe an.'
    )


class BulkAddBestandForm(MIZAdminForm):
    """The form to add a 'bestand' to a model instance."""

    # TODO: BulkAddBestandForm is probably outdated?
    bestand = forms.ModelChoiceField(
        required = True,
        label = "Lagerort (Bestand)",
        queryset = lagerort.objects.all(),
        widget = make_widget(model=lagerort, wrap=True)
    )
    dublette = forms.ModelChoiceField(
        required = True,
        label = "Lagerort (Dublette)",
        queryset = lagerort.objects.all(),
        widget = make_widget(model=lagerort, wrap=True)
    )


class MergeFormSelectPrimary(DynamicChoiceFormMixin, MIZAdminForm):
    """
    A merge form that lets the user select the 'primary' object.

    Fields:
        primary (ChoiceField): the object that other objects
            will be merged into.
        expand_o (BooleanField): whether or not to expand the primary
            object with data from the other objects.
    """

    primary = forms.ChoiceField(
        choices = [],
        label = 'Primären Datensatz auswählen',
        widget = forms.RadioSelect(),
        help_text = "Bitten wählen Sie den Datensatz, dem die verwandten "
        "Objekte der anderen Datensätze angehängt werden sollen."
    )
    expand_o = forms.BooleanField(
        required = False,
        label = 'Primären Datensatz erweitern',
        initial=True,
        help_text = "Sollen fehlende Grunddaten des primäre Datensatzes um "
        "in anderen Datensätzen vorhandenen Daten erweitert werden?"
    )


class MergeFormHandleConflicts(DynamicChoiceFormMixin, MIZAdminForm):
    """
    The form that resolves merge conflicts for one model field.

    Fields:
        original_fld_name (HiddenInput): stores the name of the field
        verbose_fld_name (HiddenInput): stores the verbose name of the field
        posvals (ChoiceField): the different possible values for this field;
            its choices are set from init kwargs using DynamicChoiceFormMixin
    """

    original_fld_name = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    verbose_fld_name = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )
    posvals = forms.ChoiceField(
        choices = [],
        label = 'Mögliche Werte',
        widget = forms.RadioSelect()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Try to add a more accurate label to the posvals field.
        if self.data.get(self.add_prefix('verbose_fld_name')):
            self.fields['posvals'].label = 'Mögliche Werte für {}:'.format(
                self.data.get(self.add_prefix('verbose_fld_name')))

MergeConflictsFormSet = forms.formset_factory(
    MergeFormHandleConflicts, extra=0, can_delete=False
)


class BrochureActionForm(MIZAdminForm):
    """
    The form to move an ausgabe instance to any of the brochure models.

    Fields:
        ausgabe_id (HiddenInput): id of the instance
        titel (CharField): value for the 'titel' model field of a brochure
        beschreibung (CharField): as above
        bemerkungen (CharField): as above
        zusammenfassung (CharField): as above
        accept (BooleanField): confirm the changes for this instance
    """

    textarea_config = {'rows': 2, 'cols': 90}

    ausgabe_id = forms.IntegerField(widget = forms.HiddenInput())
    titel = forms.CharField(widget = forms.Textarea(attrs=textarea_config))

    beschreibung = forms.CharField(
        widget = forms.Textarea(attrs=textarea_config), required = False)

    bemerkungen = forms.CharField(
        widget = forms.Textarea(attrs=textarea_config), required = False)

    zusammenfassung = forms.CharField(
        widget = forms.Textarea(attrs=textarea_config), required = False)

    accept = forms.BooleanField(
        label = 'Änderungen bestätigen',
        required = False,
        initial = True,
        help_text = "Hiermit bestätigen Sie, dass diese Ausgabe verschoben "
        "werden soll. Entfernen Sie das Häkchen, um diese Ausgabe zu "
        "überspringen und nicht zu verschieben."
    )

    fieldsets = [(None, {'fields': [
        'ausgabe_id', ('titel', 'zusammenfassung'),
        ('beschreibung', 'bemerkungen'), 'accept'
    ]})]

BrochureActionFormSet = forms.formset_factory(
    form = BrochureActionForm,
    formset = forms.BaseFormSet,
    extra = 0,
    can_delete = True
)


class BrochureActionFormOptions(MIZAdminForm):
    """
    The form that displays additional options for moving ausgaben to brochure.

    Fields:
        brochure_art (ChoiceField): select the subtype of brochure to move to.
        delete_magazin (BooleanField): whether to delete the magazin the
            ausgabe instances belong to after moving.
            If the magazin instance would be protected from deletion, the
            field will not be displayed.
    """

    def brochure_choices():
        from DBentry.models import Brochure, Kalendar, Katalog
        return [
            (Brochure._meta.model_name, Brochure._meta.verbose_name),
            (Katalog._meta.model_name, Katalog._meta.verbose_name),
            (Kalendar._meta.model_name, Kalendar._meta.verbose_name),
        ]

    brochure_art = forms.ChoiceField(
        label = 'Verschieben nach', choices = brochure_choices)

    delete_magazin = forms.BooleanField(
        label = 'Magazin löschen',
        required = False,
        help_text = 'Soll das Magazin dieser Ausgaben anschließend gelöscht werden?'
    )

    def __init__(self, can_delete_magazin = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_delete_magazin:
            del self.fields['delete_magazin']

    def clean_brochure_art(self):
        """Make sure the user has selected a valid model."""
        value = self.cleaned_data.get('brochure_art')
        if get_model_from_string(value) is None:
            raise ValidationError("%s ist kein zulässiges Model." % value)
        return value
