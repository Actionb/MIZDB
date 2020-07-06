from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError

from DBentry import models as _models
from DBentry.ac.widgets import make_widget
from DBentry.base.forms import MIZAdminFormMixin, MinMaxRequiredFormMixin
from DBentry.constants import discogs_release_id_pattern
from DBentry.validators import DiscogsURLValidator


class AusgabeMagazinFieldForm(forms.ModelForm):
    """
    An abstract model form that adds a 'ausgabe__magazin' field which is used
    to limit (forward) the choices available to the widget of a field 'ausgabe'.

    Also adds the ausgabe's magazin to the form's initial data (if applicable).
    Useable by any ModelForm that uses a relation to ausgabe.
    """

    ausgabe__magazin = forms.ModelChoiceField(
        required=False,
        label="Magazin",
        queryset=_models.magazin.objects.all(),
        widget=make_widget(
            model=_models.magazin, wrap=True, can_delete_related=False
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
        model = _models.artikel
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
        'max': 1, 'fields': ['is_buchband', 'buchband'],
        'error_messages': {'max': 'Ein Buchband kann nicht selber Teil eines Buchbandes sein.'}
    }]

    class Meta:
        widgets = {
            'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90}),
            'titel_orig': forms.Textarea(attrs={'rows': 1, 'cols': 90}),
            'buchband': make_widget(
                url='acbuchband', model=_models.buch, wrap=False,
                can_delete_related=False
            ),
        }


class HerausgeberForm(MinMaxRequiredFormMixin, forms.ModelForm):
    minmax_required = [{'fields': ['person', 'organisation'], 'min': 1}]


class AudioForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['discogs_url'].validators.append(DiscogsURLValidator())

    def clean(self):
        """Validate and clean release_id and discogs_url."""
        # release_id and discogs_url are not required, so that leaves two
        # possibilities why they not turn up in self.cleaned_data at this point:
        # - they simply had no data
        # - the data they had was invalid
        release_id = str(self.cleaned_data.get('release_id', '') or '')
        discogs_url = self.cleaned_data.get('discogs_url') or ''
        # There is no point in working on empty or invalid data, so return early.
        if (not (release_id or discogs_url)
                or 'release_id' in self._errors
                or 'discogs_url' in self._errors):
            return self.cleaned_data
        match = discogs_release_id_pattern.search(discogs_url)
        if match and len(match.groups()) == 1:
            # We have a valid url with a release_id in it.
            release_id_from_url = match.groups()[-1]
            if release_id and release_id_from_url != release_id:
                raise ValidationError(
                    "Die angegebene Release ID stimmt nicht mit der ID im "
                    "Discogs Link überein."
                )
            elif not release_id:
                # Set release_id from the url.
                release_id = str(match.groups()[-1])
                self.cleaned_data['release_id'] = release_id
        discogs_url = "http://www.discogs.com/release/" + release_id
        self.cleaned_data['discogs_url'] = discogs_url
        return self.cleaned_data


class BildmaterialForm(forms.ModelForm):
    """
    The form for the bildmaterial's admin add/change page.
    A BooleanField is added with which the user can request to copy all related
    musiker/band objects of the related veranstaltung instances to this
    bildmaterial instance.
    """

    copy_related = forms.BooleanField(
        label='Bands/Musiker kopieren',
        help_text=('Setzen Sie das Häkchen, um Bands und Musiker der '
            'Veranstaltungen direkt zu diesem Datensatz hinzuzufügen.'),
        required=False
    )

    class Meta:
        widgets = {'titel': forms.Textarea(attrs={'rows': 1, 'cols': 90})}


class FavoritenForm(MIZAdminFormMixin, forms.ModelForm):
    class Meta:
        model = _models.Favoriten
        fields = '__all__'
        widgets = {
            'fav_genres': FilteredSelectMultiple('Genres', False),
            'fav_schl': FilteredSelectMultiple('Schlagworte', False),
        }
