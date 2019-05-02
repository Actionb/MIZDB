from django import forms 
from django.contrib.admin.widgets import FilteredSelectMultiple
from .widgets import ColumnedCheckboxWidget
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
#        widget =  FilteredSelectMultiple('Felder', False), 
        help_text = 'Wähle die Felder, deren Werte in die Suche miteinbezogen werden sollen.', 
        label = '', 
        widget = forms.CheckboxSelectMultiple
    )
    m2m_fields = forms.MultipleChoiceField(
#        widget = FilteredSelectMultiple('Mehrfach-Beziehungen', False), 
        help_text = "BLABLA", 
        label = 'Mehrfach-Beziehungen', 
        widget = forms.CheckboxSelectMultiple
    )
    
    fieldsets = [('Felder', {'fields': ['fields', 'm2m_fields'], 'classes': ['collapse']})]
    
    @property
    def fieldsets(self):
        classes = ['collapse']
        if self.initial.get('fields', False) or self.initial.get('m2m_fields', False):
            classes.append('collapsed')
        return [('Felder', {'fields': ['fields', 'm2m_fields'], 'classes': classes})]

class DuplicateFieldsSelectForm(MIZAdminForm):
    #TODO: MIZAdminForm creates fieldsets for the fields; fieldsets implicitly add a label even if the label of a field is ''
    fields = forms.MultipleChoiceField(
#        widget =  FilteredSelectMultiple('Felder', False), 
        help_text = 'Wähle die Felder, deren Werte in die Suche miteinbezogen werden sollen.', 
        label = '', 
        widget = ColumnedCheckboxWidget
    )

    @property
    def fieldsets(self):
        classes = ['collapse']
        if self.initial.get('fields', False):
            classes.append('collapsed')
        return [('Felder', {'fields': ['fields'], 'classes': classes})]
    
class ModelSelectForm(MIZAdminForm):
    
    def get_model_list():
        #TODO: review this
        from django.apps import apps
        rslt = []
        for model in apps.get_models('DBentry'):
            if model.__module__ == 'DBentry.models' and not model._meta.auto_created\
            and 'alias' not in model._meta.model_name\
            and model._meta.verbose_name not in ('favoriten', 'lfd. Nummer', 'Ausgabe-Monat', 'Nummer'):
                rslt.append((model._meta.model_name, model._meta.verbose_name))
        return [('', '')] + sorted(rslt, key=lambda tpl:tpl[1])
        
    model_select = forms.ChoiceField(choices = get_model_list, label = 'Bitte das Modell auswählen', initial = '')
