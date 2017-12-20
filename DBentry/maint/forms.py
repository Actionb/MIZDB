from django import forms 
from DBentry.forms import MIZAdminForm, DynamicChoiceForm, DynamicChoiceFormSet 
 
class MaintBaseForm(forms.Form): 
    pass 
     
class MergeFormBase(DynamicChoiceForm, MIZAdminForm): 
    pass
     
class MergeFormSelectPrimary(MergeFormBase): 
    original = forms.ChoiceField(choices = [], label = 'Primären Datensatz auswählen', widget = forms.RadioSelect()) 
    expand_o = forms.BooleanField(required = False, label = 'Primären Datensatz erweitern') 
     
class MergeFormHandleConflicts(MergeFormBase): 
    original_fld_name = forms.CharField(required=False, widget=forms.HiddenInput()) # Stores the name of the field 
    verbose_fld_name = forms.CharField(label = 'Original-Feld', widget=forms.TextInput(attrs={'readonly':'readonly'})) # Displays the verbose name of the field 
    posvals = forms.ChoiceField(choices = [], label = 'Mögliche Werte', widget = forms.RadioSelect()) 
     
     
#MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, formset = DynamicChoiceFormSet, extra=0, can_delete=False) 
MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, extra=0, can_delete=False)   
   
