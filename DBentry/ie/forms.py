from django import forms
from DBentry.base.forms import MIZAdminForm

class ImportSelectForm(MIZAdminForm):
    import_file = forms.FileField(allow_empty_file=False)
    check_bom = forms.BooleanField(required = False)

class MBForm(MIZAdminForm):
    name = forms.CharField()
    release_ids = forms.CharField(required=False, widget=forms.HiddenInput()) 
    
    is_musiker = forms.BooleanField(label = 'Ist Musiker', required=False)
    is_band = forms.BooleanField(label = 'Ist Band', required=False)
    is_person = forms.BooleanField(label = 'Ist Person', required=False)
    
    def clean(self):
        is_band = self.cleaned_data.get('is_band', False)
        is_musiker = self.cleaned_data.get('is_musiker', False)
        is_person = self.cleaned_data.get('is_person', False)
        
        if is_band and is_person:
            raise ValidationError('Eine Band kann nicht auch eine Person sein.')
            
        if is_band and is_musiker:
            raise ValidationError('Eine Band kann nicht auch ein Musiker sein.')
            
        if not is_band and not is_musiker and not is_person:
            raise ValidationError('Bitte diesen Namen zuweisen.')
    
MBFormSet = forms.formset_factory(MBForm, extra=0, can_delete=True)
