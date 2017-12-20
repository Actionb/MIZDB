from django import forms 
from DBentry.forms import MIZAdminForm, DynamicChoiceForm, DynamicChoiceFormSet 
 
class MaintBaseForm(forms.Form): 
    pass 
     
class MergeFormBase(DynamicChoiceForm, MIZAdminForm): 
     
    qs = None 
    model = None 
     
#    def __init__(self, qs = None, *args, **kwargs): 
#        if qs: 
#            kwargs['qs'] = qs 
#            self.qs = qs 
#            self.model = qs.model 
#        super(MergeFormBase, self).__init__(*args, **kwargs) 
     
class MergeFormSelectPrimary(MergeFormBase): 
    original = forms.ChoiceField(choices = [], label = 'Primären Datensatz auswählen', widget = forms.RadioSelect()) 
    expand_o = forms.BooleanField(required = False, label = 'Primären Datensatz erweitern') 
     
#    def __init__(self, qs = None, *args, **kwargs): 
#        #kwargs['original'] = qs 
#        super(MergeFormSelectPrimary, self).__init__(qs, *args, **kwargs) 
##        if self.qs: 
##            self.fields['original'].choices = [(i.pk, i.__str__()) for i in self.qs] 
             
class MergeFormHandleConflicts(MergeFormBase): 
    original_fld_name = forms.CharField(required=False, widget=forms.HiddenInput()) # Stores the name of the field 
    verbose_fld_name = forms.CharField(label = 'Original-Feld', widget=forms.TextInput(attrs={'readonly':'readonly'})) # Displays the verbose name of the field 
    posvals = forms.ChoiceField(choices = [], label = 'Mögliche Werte', widget = forms.RadioSelect()) 
     
#    def __init__(self, *args, **kwargs): 
#        print('form') 
#        print('kwargs', kwargs) 
#        super(MergeFormHandleConflicts, self).__init__(*args, **kwargs) 
#        print('data', self.data) 
#        for fld_name in self.fields: 
#            try: 
#                print(fld_name, self[fld_name].value()) 
#            except: 
#                pass 
 
     
MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, formset = DynamicChoiceFormSet, extra=0, can_delete=False) 
MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, extra=0, can_delete=False)   
   
from DBentry.models import ausgabe 
class MergePrimary(MIZAdminForm, forms.ModelForm): 
     
    class Meta: 
        model = ausgabe 
        fields = '__all__' 
        exclude = ['audio'] 