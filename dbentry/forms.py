from dal import autocomplete
from django import forms
from django.core.exceptions import ValidationError

from dbentry import models as _models
from dbentry.ac.widgets import make_widget
from dbentry.base.forms import MinMaxRequiredFormMixin, DiscogsFormMixin
from dbentry.utils.gnd import searchgnd
from dbentry.validators import DNBURLValidator


class GoogleBtnWidget(forms.widgets.TextInput):
    """
    A TextInput widget with a button which opens a google search for what is
    typed into the TextInput.
    """

    template_name = 'googlebuttonwidget.html'

    class Media:
        js = ('admin/js/googlebtn.js', )


class AusgabeMagazinFieldForm(forms.ModelForm):
    """
    An abstract model form that adds a 'ausgabe__magazin' field which is used
    to limit (forward) the choices available to the widget of a field 'ausgabe'.

    Also adds the ausgabe's magazin to the form's initial data (if applicable).
    Usable by any ModelForm that uses a relation to ausgabe.
    """

    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.Magazin.objects.all(),
        widget=make_widget(
            model=_models.Magazin, wrap=True, can_delete_related=False
        )
    )

    class Meta:
        widgets = {
            'ausgabe': make_widget(
                model_name='ausgabe',
                forward=['ausgabe__magazin']
            )
        }

    def __init__(self, *args, **kwargs):
        """Set the initial for ausgabe__magazin according to the form's instance."""
        if 'instance' in kwargs and kwargs['instance']:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            if kwargs['instance'].ausgabe:
                kwargs['initial']['ausgabe__magazin'] = (
                    kwargs['instance'].ausgabe.magazin)
        super().__init__(*args, **kwargs)


class ArtikelForm(AusgabeMagazinFieldForm):
    class Meta:
        model = _models.Artikel
        fields = '__all__'
        widgets = {
            'ausgabe': make_widget(
                model_name='ausgabe', forward=['ausgabe__magazin']),
            'schlagzeile': forms.Textarea(attrs={'rows': 2, 'cols': 90}),
        }


class AutorForm(MinMaxRequiredFormMixin, forms.ModelForm):
    minmax_required = [{'min': 1, 'fields': ['kuerzel', 'person']}]


class BrochureForm(AusgabeMagazinFieldForm):
    class Meta:
        widgets = {
            'ausgabe': make_widget(
                model_name='ausgabe', forward=['ausgabe__magazin']),
            'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})
        }


class BuchForm(MinMaxRequiredFormMixin, forms.ModelForm):
    minmax_required = [{
        'max': 1,
        'fields': ['is_buchband', 'buchband'],
        'error_messages': {
            'max': 'Ein Buchband kann nicht selber Teil eines Buchbandes sein.'
        }
    }]

    class Meta:
        widgets = {
            'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90}),
            'titel_orig': forms.Textarea(attrs={'rows': 1, 'cols': 90})
        }

    def clean_is_buchband(self):
        """
        Only allow setting 'is_buchband' to False for instances that aren't
        referenced by other Buch instances.

        If this form's instance was flagged as a Buchband and other Buch
        instances refer to it as their Buchband, setting is_buchband to False
        would end up making the forms of the related instances invalid:
        the selected Buchband would not be a valid choice anymore as the choices
        are limited to {'is_buchband': True} (see the model field).
        """
        is_buchband = self.cleaned_data.get('is_buchband', False)
        if not is_buchband and self.instance.buch_set.exists():
            raise ValidationError(
                "Nicht abwählbar für Buchband mit existierenden Aufsätzen.",
                code='invalid'
            )
        return is_buchband


class MusikerForm(forms.ModelForm):
    class Meta:
        widgets = {'kuenstler_name': GoogleBtnWidget()}


class BandForm(forms.ModelForm):
    class Meta:
        widgets = {'band_name': GoogleBtnWidget()}


class AudioForm(DiscogsFormMixin, forms.ModelForm):
    url_field_name = 'discogs_url'
    release_id_field_name = 'release_id'
    class Meta:
        widgets = {'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})}


class VideoForm(DiscogsFormMixin, forms.ModelForm):
    url_field_name = 'discogs_url'
    release_id_field_name = 'release_id'
    class Meta:
        widgets = {'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})}


class PlakatForm(forms.ModelForm):
    """
    The form for the plakat's admin add/change page.
    A BooleanField is added with which the user can request to copy all related
    Musiker/Band objects of the related veranstaltung instances to this
    plakat instance.
    """

    copy_related = forms.BooleanField(
        label='Bands/Musiker kopieren',
        help_text=(
            'Setzen Sie das Häkchen, um Bands und Musiker der '
            'Veranstaltungen direkt zu diesem Datensatz hinzuzufügen.'
        ),
        required=False
    )

    class Meta:
        widgets = {'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})}


class FotoForm(forms.ModelForm):
    class Meta:
        widgets = {'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})}


class PersonForm(forms.ModelForm):
    class Meta:
        widgets = {
                'gnd_id': autocomplete.Select2(url='gnd'),
                'gnd_name': forms.HiddenInput()
        }

    url_validator_class = DNBURLValidator

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['dnb_url'].validators.append(self.url_validator_class())
        if self.instance.pk:
            # Set the initial (selected) choice.
            self.fields['gnd_id'].widget.choices = [
                (self.instance.gnd_id, self.instance.gnd_name)]

    def clean(self):
        """Validate and clean gnd_id and dnb_url."""
        if ('dnb_url' in self._errors
                or 'gnd_id' in self._errors):
            return self.cleaned_data
        gnd_id = self.cleaned_data.get('gnd_id', '')
        dnb_url = self.cleaned_data.get('dnb_url', '')
        if not (gnd_id or dnb_url):
            return self.cleaned_data

        match = self.url_validator_class.regex.search(dnb_url)
        if match and len(match.groups()) == 1:
            # The URL is valid and has a gnd_id.
            # The validator doesn't allow URLs without at least a one digit ID.
            gnd_id_from_url = match.groups()[-1]

            if 'gnd_id' in self.changed_data and 'dnb_url' in self.changed_data:
                if not gnd_id:
                    # gnd_id was 'removed'. Set it from the new URL.
                    gnd_id = gnd_id_from_url
                    self.cleaned_data['gnd_id'] = gnd_id
                elif gnd_id_from_url != gnd_id:
                    # The values of both fields have changed, but the IDs do 
                    # not match.
                    raise ValidationError(
                        "Die angegebene GND ID (%s) stimmt nicht mit der ID im "
                        "DNB Link überein (%s)." % (gnd_id, gnd_id_from_url)
                    )
            elif 'dnb_url' in self.changed_data:
                # Only dnb_url was changed; update gnd_id accordingly.
                gnd_id = gnd_id_from_url
                self.cleaned_data['gnd_id'] = gnd_id

        # Validate the gnd_id by checking that a SRU query with it returns
        # a single match.
        results, _c = searchgnd(query="nid=" + gnd_id)
        if len(results) != 1:
            raise ValidationError("Die GND ID ist ungültig.")
        # Store the result's label for later use as data for the model field
        # 'gnd_name'.
        self.cleaned_data['gnd_name'] = results[0][1]
        # Normalize the URL to the DNB permalink.
        dnb_url = "http://d-nb.info/gnd/" + gnd_id
        self.cleaned_data['dnb_url'] = dnb_url
        return self.cleaned_data
