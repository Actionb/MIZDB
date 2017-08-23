from django import forms
from django.forms import modelform_factory, Textarea

from .models import *
from .constants import *

from dal import autocomplete

WIDGETS = { 'person' : autocomplete.ModelSelect2(url='acperson'), 
            'genre' : autocomplete.ModelSelect2(url='acgenre'),  
            'schlagwort' : autocomplete.ModelSelect2(url='acschlagwort'), 
            'autor' : autocomplete.ModelSelect2(url='acautor'), 
            
            
            
            # Artikel
            'ausgabe' : autocomplete.ModelSelect2(url='acausgabe'), 
            
            # Audio
            'sender' : autocomplete.ModelSelect2(url='acsender'), 
            
            # Ausgaben
            'magazin' : autocomplete.ModelSelect2(url='acmagazin'),
            
            # Band
            'musiker' : autocomplete.ModelSelect2(url='acmusiker'),
            
            # Bestand
            bestand : {
                'ausgabe' : autocomplete.ModelSelect2(url = 'acausgabe'), 
                'buch' : autocomplete.ModelSelect2(url='acbuch'),  
                'lagerort' :  autocomplete.ModelSelect2(url='aclagerort'), 
                'provenienz' : autocomplete.ModelSelect2(url='acprov'), 
            }, 
            
            # Buch
            buch : {
                'verlag' : autocomplete.ModelSelect2(url='acverlag'), 
                'verlag_orig' : autocomplete.ModelSelect2(url='acverlag'), 
                'sprache' : autocomplete.ModelSelect2(url='acsprache'), 
                'sprache_orig' : autocomplete.ModelSelect2(url='acsprache'),
                'buch_serie' : autocomplete.ModelSelect2(url='acbuchserie'),
            }, 
            
            # Genre
            genre : {
                'ober' : autocomplete.ModelSelect2(url='acgenre'),
            }, 
            
            # Magazin
            magazin : {
                'verlag' : autocomplete.ModelSelect2(url='acverlag'), 
                'genre' : autocomplete.ModelSelect2Multiple(url='acgenre'), 
                'ort' : autocomplete.ModelSelect2(url='acort'), 
                'info' : Textarea(attrs=ATTRS_TEXTAREA),
                'beschreibung' : Textarea(attrs=ATTRS_TEXTAREA),
            }, 
            
            # Musiker
            'instrument' : autocomplete.ModelSelect2(url='acinstrument'),
            'band' : autocomplete.ModelSelect2(url='acband'), 
            
            # Orte
            'herkunft' : autocomplete.ModelSelect2(url='acort'), 
            'ort' : autocomplete.ModelSelect2(url='acort'), 
            'kreis' : autocomplete.ModelSelect2(url='ackreis'), 
            'bland' : autocomplete.ModelSelect2(url='acbland', forward=['land'], attrs = {'data-placeholder': 'Bitte zuerst ein Land auswählen!'}), 
            'land' : autocomplete.ModelSelect2(url='acland'), 
            'veranstaltung' : autocomplete.ModelSelect2(url='acveranstaltung'), 
            'spielort' : autocomplete.ModelSelect2(url='acspielort'), 
            'sitz' : autocomplete.ModelSelect2(url='acort'),
            
            # Prov/Lagerort
            'lagerort' : autocomplete.ModelSelect2(url='aclagerort'), 
            provenienz : {
                'geber' : autocomplete.ModelSelect2(url='acgeber'), 
            }, 
            'provenienz' : autocomplete.ModelSelect2(url='acprov'), 
            
            # Schlagworte
            schlagwort : {
                'ober' : autocomplete.ModelSelect2(url='acschlagwort'),  
            }, 
            # Sonstige 
            'sender'        : autocomplete.ModelSelect2(url='acsender'), 
            'beschreibung'  : Textarea(attrs=ATTRS_TEXTAREA), 
            'info'          : Textarea(attrs=ATTRS_TEXTAREA), 
            
            
}

class FormBase(forms.ModelForm):
    
    #TODO: __init__ set initial values from _changelist_filters
    
    def validate_unique(self):
        """
        Calls the instance's validate_unique() method and updates the form's
        validation errors if any were raised.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            # Ignore non-unique entries in the same set
            self.cleaned_data['DELETE']=True
            self._update_errors(e)

def makeForm(model, fields = []):
    fields_param = fields or '__all__'
    import sys
    modelname = model._meta.model_name
    thismodule = sys.modules[__name__]
    formname = '{}Form'.format(str(modelname).capitalize())
    #Check if a proper Form already exists:
    if hasattr(thismodule, formname):
        return getattr(thismodule, formname)
    
    #Otherwise use modelform_factory to create a generic Form with custom widgets
    widget_list =  WIDGETS
    if model in WIDGETS:
        widget_list = WIDGETS[model]
    return modelform_factory(model = model, form=FormBase, fields = fields_param, widgets = widget_list) 
    


class ArtikelForm(forms.ModelForm):
        
    magazin = forms.ModelChoiceField(required = False, 
                                    queryset = magazin.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmagazin'))
                                    
    class Meta:
        model = artikel
        fields = '__all__'
        widgets = {
                'ausgabe' : autocomplete.ModelSelect2(url='acausgabe', forward = ['magazin'], 
                    attrs = {'data-placeholder': 'Bitte zuerst ein Magazin auswählen!'}), 
                'schlagzeile'       : Textarea(attrs={'rows':2, 'cols':90}), 
                'zusammenfassung'   : Textarea(attrs=ATTRS_TEXTAREA), 
                'info'              : Textarea(attrs=ATTRS_TEXTAREA), 
        }
        
    def __init__(self, *args, **kwargs):
        initial = dict()
        if not 'initial' in kwargs:
            kwargs['initial'] = dict()
        if 'instance' in kwargs:
            # Form is bound to a specific instance
            if  hasattr(kwargs['instance'], 'artikel_magazin'):
                # Set the right magazine for the instance's change_form
                initial = {'magazin' : kwargs['instance'].artikel_magazin()}
        else:
            # Add-Form
            if '_changelist_filters' in kwargs['initial']:
                d = kwargs['initial']['_changelist_filters']
                # initial contains the _changelist_filters dict created by the search form/search term
                initial['ausgabe'] = d.get('ausgabe', None)
                if initial['ausgabe']:
                    initial['magazin'] = ausgabe.objects.get(pk=initial['ausgabe']).magazin
                else:
                    initial['magazin'] = d.get('ausgabe__magazin', None)
                initial['seite'] = d.get('seite', None)
        kwargs['initial'].update(initial)
        super(ArtikelForm, self).__init__(*args, **kwargs)
