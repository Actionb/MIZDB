from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple

from DBentry import models as _models
from DBentry.base.forms import FormBase, MIZAdminForm, XRequiredFormMixin
from DBentry.constants import ATTRS_TEXTAREA, discogs_release_id_pattern  
from DBentry.ac.widgets import make_widget

Textarea = forms.Textarea           

class AusgabeMagazinFieldForm(FormBase):
    """
    In order to limit search results, forward ausgabe search results to a ModelChoiceField for the model magazin.
    Useable by any ModelForm that uses a relation to ausgabe.
    Any form that inherits AusgabeMagazinFieldMixin.Meta and declares widgets in its inner Meta, must also redeclare the widget for ausgabe.
    As such, it is not very useful to inherit the Meta.    (Python inheritance rules apply)
    """
    ausgabe__magazin = forms.ModelChoiceField(required = False,
                                    label = "Magazin", 
                                    queryset = _models.magazin.objects.all(), 
                                    widget = make_widget(
                                        model=_models.magazin, wrap=True, can_delete_related=False
                                    ))
    class Meta:
        widgets = {'ausgabe': make_widget(model_name = 'ausgabe', forward = ['ausgabe__magazin'])}

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance']:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            if kwargs['instance'].ausgabe:
                kwargs['initial']['ausgabe__magazin'] = kwargs['instance'].ausgabe.magazin
        super().__init__(*args, **kwargs)

class ArtikelForm(AusgabeMagazinFieldForm):
    class Meta:
        model = _models.artikel
        fields = '__all__'
        widgets = {
                'ausgabe': make_widget(model_name = 'ausgabe', forward = ['ausgabe__magazin']),               
                'schlagzeile'       : Textarea(attrs={'rows':2, 'cols':90}), 
                'zusammenfassung'   : Textarea(attrs=ATTRS_TEXTAREA), 
                'info'              : Textarea(attrs=ATTRS_TEXTAREA), 
        }

class AutorForm(XRequiredFormMixin, FormBase):

    xrequired = [{'min':1, 'fields':['kuerzel', 'person']}]

class BrochureForm(AusgabeMagazinFieldForm):
    class Meta:
        widgets = {
            'ausgabe': make_widget(model_name = 'ausgabe', forward = ['ausgabe__magazin']), 
            'titel': Textarea(attrs={'rows':1, 'cols':90})
        }

class BuchForm(XRequiredFormMixin, FormBase):
    class Meta:
        widgets = {
            'titel' : Textarea(attrs={'rows':1, 'cols':90}), 
            'titel_orig': Textarea(attrs={'rows':1, 'cols':90}), 
            'buchband' : make_widget(
                url='acbuchband', model=_models.buch, wrap=False, can_delete_related=False
            ),
        }

    xrequired = [{
        'max':1, 'fields': ['is_buchband', 'buchband'], 
        'error_message': {'max': 'Ein Buchband kann nicht selber Teil eines Buchbandes sein.'}
    }]

class HerausgeberForm(XRequiredFormMixin, FormBase):

    xrequired = [{'fields':['person', 'organisation'], 'min':1}]

class AudioForm(FormBase):   

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from DBentry.validators import DiscogsURLValidator
        self.fields['discogs_url'].validators.append(DiscogsURLValidator())

    def clean(self):
        # release_id and discogs_url are not required, so there's two reason they might not turn up in self.cleaned_data at this point:
        # - they simply had no data
        # - the data they had was invalid
        release_id = str(self.cleaned_data.get('release_id', '') or '') # cleaned_data['release_id'] is either an int or None 
        discogs_url = self.cleaned_data.get('discogs_url') or ''

        # There is no point in working on empty or invalid data, so return early.
        if not (release_id or discogs_url) or 'release_id' in self._errors or 'discogs_url' in self._errors:
            return self.cleaned_data

        match = discogs_release_id_pattern.search(discogs_url) # cleaned_data['discogs_url'] could be None therefore: or ''
        if match and len(match.groups()) == 1:
            # We have a valid url with a release_id in it
            release_id_from_url = match.groups()[-1]
            if release_id and release_id_from_url != release_id:
                raise ValidationError("Die angegebene Release ID stimmt nicht mit der ID im Discogs Link überein.")
            elif not release_id:
                # Set release_id from the url
                release_id = str(match.groups()[-1])
                self.cleaned_data['release_id'] = release_id
        # Clean (as in: remove slugs) and set discogs_url with the confirmed release_id
        self.cleaned_data['discogs_url'] = "http://www.discogs.com/release/" + release_id

        return self.cleaned_data

class BildmaterialForm(FormBase):
    copy_related = forms.BooleanField(
        label = 'Bands/Musiker kopieren', 
        help_text = 'Setzen Sie das Häkchen, um Bands und Musiker der Veranstaltungen direkt zu diesem Datensatz hinzuzufügen.', 
        required = False
    )

    class Meta:
        widgets = {
            'titel': Textarea(attrs={'rows':1, 'cols':90})
        }

#TODO: mro() is bad: forms.Form comes before forms.ModelForm and its descendants        
# Arent we using ModelForm just to save the formfield declarations?
class FavoritenForm(MIZAdminForm, forms.ModelForm):
    class Meta:
        model = _models.Favoriten
        fields = '__all__'
        widgets = {
            'fav_genres'    :   FilteredSelectMultiple('Genres', False), 
            'fav_schl'      :   FilteredSelectMultiple('Schlagworte', False),
        }
