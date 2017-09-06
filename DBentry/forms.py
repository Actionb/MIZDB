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
    
    def __init__(self, *args, **kwargs):
        # the change_form's (for add forms) initial data is being cleaned and provided by the method ModelBase.get_changeform_initial_data
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        initial = kwargs['initial'].copy()
        
        # since the ModelBase does not know what the formfields of its change_form are called, we may need to compare the
        # keys given in initial to the fields of the form in order to find a match
        fld_names = set(self.base_fields.keys())
        
        for k, v in initial.items():
            if k in fld_names:
                # This particular item in initial has a definitive match to a formfield
                fld_names.remove(k)
                continue
            
            # k might be a field_path, e.g. ausgabe__magazin
            for fld_name in fld_names:
                if fld_name == k.split('__')[-1]:
                    kwargs['initial'][fld_name] = v
                    break
                    
            # Remove all the field names that have already been matched, so we do not override the match with a  
            # partial match in name in subsequent loops
            fld_names = fld_names.difference(kwargs['initial'].keys())
            
            # Try to find a partial match in name, last resort
            for fld_name in fld_names:
                if fld_name in k:
                    kwargs['initial'][fld_name] = v 
                    break
                    
            fld_names = fld_names.difference(kwargs['initial'].keys())
        super(FormBase, self).__init__(*args, **kwargs)
                
            
    
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
    


class ArtikelForm(FormBase):
        
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
