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
    return modelform_factory(model = model, fields = fields_param, widgets = widget_list) 
    
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
                'zusammenfassung'   : Textarea(attrs=ATTRS_TEXTAREA), 
                'info'              : Textarea(attrs=ATTRS_TEXTAREA), 
        }
        
    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and hasattr(kwargs['instance'], 'artikel_magazin'):
            initial = {'magazin' : kwargs['instance'].artikel_magazin()}
            kwargs['initial'] = initial
        super(ArtikelForm, self).__init__(*args, **kwargs)
        
