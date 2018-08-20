from django import forms 
from django.contrib.admin.widgets import FilteredSelectMultiple

from DBentry.forms import MIZAdminForm, DynamicChoiceForm 

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
   
class DuplicateFieldsSelectForm(MIZAdminForm, DynamicChoiceForm):
    fields = forms.MultipleChoiceField(
        widget =  FilteredSelectMultiple('Felder', False), 
        help_text = 'Wähle die Felder, deren Werte in die Suche miteinbezogen werden sollen.', 
        label = 'Felder'
    )
    
class ModelSelectForm(MIZAdminForm):
    
    def get_model_list():
        from django.apps import apps
        rslt = []
        for model in apps.get_models('DBentry'):
            if model.__module__ == 'DBentry.models' and not model._meta.auto_created\
            and 'alias' not in model._meta.model_name\
            and model._meta.verbose_name not in ('favoriten', 'lfd. Nummer', 'Ausgabe-Monat', 'Nummer'):
                rslt.append((model._meta.model_name, model._meta.verbose_name))
        return [('', '')] + sorted(rslt, key=lambda tpl:tpl[1])
        
    model_select = forms.ChoiceField(choices = get_model_list, label = 'Bitte das Modell auswählen', initial = '')
