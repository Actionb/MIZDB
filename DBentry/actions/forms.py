
from collections import OrderedDict

from django import forms
from django.contrib.admin.utils import get_fields_from_path

from DBentry.forms import MIZAdminForm, DynamicChoiceForm
from DBentry.models import lagerort
from DBentry.ac.widgets import make_widget

def makeSelectionForm(model, fields, help_texts = None, labels = None, formfield_classes = None):
    if help_texts is None: help_texts = {}
    if labels is None: labels = {}
    if formfield_classes is None: formfield_classes = {}
    
    attrs = OrderedDict()
    for field_path in fields:
        field = get_fields_from_path(model, field_path)[-1]
        formfield_opts = dict(required = True, help_text = help_texts.get(field_path, ''))
        
        if field.is_relation:
            field = field.get_path_info()[-1].join_field
            formfield_opts['queryset'] = field.related_model.objects
            formfield_opts['widget'] = make_widget(model=field.model, model_name=field.model._meta.model_name, wrap=True)
        
        formfield_opts['label'] = labels.get(field_path, field.verbose_name.capitalize())
        if field_path in formfield_classes:
            attrs[field_path] = formfield_classes.get(field_path)(**formfield_opts)
        else:
            attrs[field_path] = field.formfield(**formfield_opts)
    return type('SelectionForm', (MIZAdminForm, ), attrs )

class BulkEditJahrgangForm(DynamicChoiceForm, MIZAdminForm):
    
    start = forms.ChoiceField(
        required = True, 
        choices = (), 
        label = 'Schlüssel-Ausgabe', 
        help_text = 'Wählen Sie eine Ausgabe.', 
        widget = forms.RadioSelect(), 
    )
    jahrgang = forms.IntegerField(
        required = True, 
        help_text = 'Geben Sie den Jahrgang für die oben ausgewählte Ausgabe an.'
    )
    
    
    
class BulkAddBestandForm(MIZAdminForm):
    
    bestand = forms.ModelChoiceField(required = True,
                                    label = "Lagerort (Bestand)", 
                                    queryset = lagerort.objects.all(), 
                                    widget = make_widget(model=lagerort, wrap=True))
    dublette = forms.ModelChoiceField(required = True,
                                    label = "Lagerort (Dublette)", 
                                    queryset = lagerort.objects.all(), 
                                    widget = make_widget(model=lagerort, wrap=True))


class MergeFormSelectPrimary(DynamicChoiceForm, MIZAdminForm):
    original = forms.ChoiceField(choices = [], label = 'Primären Datensatz auswählen', widget = forms.RadioSelect(), help_text = "Bitten wählen Sie den Datensatz, dem die verwandten Objekte der anderen Datensätze angehängt werden sollen.") 
    expand_o = forms.BooleanField(required = False, label = 'Primären Datensatz erweitern', initial=True, help_text = "Sollen fehlende Grunddaten des primäre Datensatzes um in anderen Datensätzen vorhandenen Daten erweitert werden?") 
     
class MergeFormHandleConflicts(DynamicChoiceForm, MIZAdminForm): 
    original_fld_name = forms.CharField(required=False, widget=forms.HiddenInput()) # Stores the name of the field 
    verbose_fld_name = forms.CharField(required=False, widget=forms.HiddenInput())# Stores the verbose name of the field 
    posvals = forms.ChoiceField(choices = [], label = 'Mögliche Werte', widget = forms.RadioSelect()) 
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.data.get(self.add_prefix('verbose_fld_name')):
            self.fields['posvals'].label = 'Mögliche Werte für {}:'.format(self.data.get(self.add_prefix('verbose_fld_name')))
            
MergeConflictsFormSet = forms.formset_factory(MergeFormHandleConflicts, extra=0, can_delete=False)    

class BrochureActionForm(MIZAdminForm):
    textarea_config = {'rows':2, 'cols':90}
    
    ausgabe_id = forms.IntegerField(widget = forms.HiddenInput())
    titel = forms.CharField(widget = forms.Textarea(attrs=textarea_config))
    beschreibung = forms.CharField(widget = forms.Textarea(attrs=textarea_config), required = False)
    bemerkungen = forms.CharField(widget = forms.Textarea(attrs=textarea_config), required = False)
    zusammenfassung = forms.CharField(widget = forms.Textarea(attrs=textarea_config), required = False)
    accept = forms.BooleanField(
        label = 'Änderungen bestätigen', required = False, initial = True, 
        help_text = 'Hiermit bestätigen Sie, dass diese Ausgabe verschoben werden soll. Entfernen Sie das Häkchen, um diese Ausgabe zu überspringen und nicht zu verschieben.'
    )
    
    fieldsets = [(None, {'fields':['ausgabe_id', ('titel', 'zusammenfassung'), ('beschreibung', 'bemerkungen'), 'accept']})]
       
BrochureActionFormSet = forms.formset_factory(form = BrochureActionForm, formset = forms.BaseFormSet, extra = 0, can_delete = True)

class BrochureActionFormOptions(MIZAdminForm):
    #TODO: base BROCHURE_CHOICES of the models inheritig base_brochure
    # so that it is guaranteed that get_model_from_string finds them; (or clean the field)
    BROCHURE_CHOICES = [('Brochure', 'Broschüre'), ('Katalog', 'Katalog'), ('Kalendar', 'Kalendar')]
    brochure_art = forms.ChoiceField(label = 'Verschieben nach', choices = BROCHURE_CHOICES)
    
    delete_magazin = forms.BooleanField(
        label = 'Magazin löschen', required = False, 
        help_text = 'Soll das Magazin dieser Ausgaben anschließend gelöscht werden?'
    )
    
    def __init__(self, can_delete_magazin = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not can_delete_magazin:
            del self.fields['delete_magazin']
