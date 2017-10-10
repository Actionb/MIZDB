from django import forms
from django.forms import modelform_factory, Textarea, TextInput,  CheckboxSelectMultiple
from django.conf import settings
from .models import *
from .constants import *

from dal import autocomplete


from django.utils.translation import ugettext_lazy as _

WIDGETS = {
            'audio'         :   autocomplete.ModelSelect2(url='acaudio'),
            'autor'         :   autocomplete.ModelSelect2(url='acautor'), 
            'bildmaterial'  :   autocomplete.ModelSelect2(url='acbildmaterial'), 
            'buch'          :   autocomplete.ModelSelect2(url='acbuch'), 
            'datei'         :   autocomplete.ModelSelect2(url='acdatei'), 
            'dokument'      :   autocomplete.ModelSelect2(url='acdokument'),  
            'genre'         :   autocomplete.ModelSelect2(url='acgenre'),  
            'memorabilien'  :   autocomplete.ModelSelect2(url='acmemorabilien'),
            'person'        :   autocomplete.ModelSelect2(url='acperson'),
            'schlagwort'    :   autocomplete.ModelSelect2(url='acschlagwort'),  
            'video'         :   autocomplete.ModelSelect2(url='acvideo'),
            
            
            
            # Artikel
            'ausgabe' : autocomplete.ModelSelect2(url='acausgabe'), 
            
            # Audio
            'sender' : autocomplete.ModelSelect2(url='acsender'), 
            
            # Ausgaben
            'magazin' : autocomplete.ModelSelect2(url='acmagazin'),
            
            # Band 
            #TODO: make this widget smaller, so the instruments fit properly... somehow
            'musiker' : autocomplete.ModelSelect2(url='acmusiker', attrs={'width':'10%'}), 
            
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
            'sender'        :   autocomplete.ModelSelect2(url='acsender'),  
            'bemerkungen'   :   Textarea(attrs=ATTRS_TEXTAREA), 
            'beschreibung'  :   Textarea(attrs=ATTRS_TEXTAREA), 
            'info'          :   Textarea(attrs=ATTRS_TEXTAREA), 
            
            #WIP
#            'format' : autocomplete.ModelSelect2(url='acformat'), 
            'plattenfirma' : autocomplete.ModelSelect2(url='aclabel'), 
            'format_typ' : autocomplete.ModelSelect2(url='acformat_typ'), 
            'format_size' : autocomplete.ModelSelect2(url='acformat_size'), 
            'noise_red' : autocomplete.ModelSelect2(url='acnoisered'), 
            
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
    
    def __init__(self, *args, **kwargs):
        # Set the right initial magazin for change forms (kwargs come with an instance)
        # super.__init__ takes care of setting initials for add forms
        if 'instance' in kwargs and kwargs['instance']:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            kwargs['initial']['magazin'] = kwargs['instance'].ausgabe.magazin
        super(ArtikelForm, self).__init__(*args, **kwargs)

bulkfield_allowed_chars = [',', '/', '%'] 
#TODO: use built-in REGEX validator?
def validate_bulkfield(value):
    """ Validator for the input fields of a Bulk Form.
        Checks if there any unallowed characters in the value (String).
    """
    for char in value:
        if not char.isnumeric() and not char in bulkfield_allowed_chars:
            from django.utils.translation import ugettext_lazy as _
            print('ValidationError')
            raise ValidationError(
                _('Unerlaubte Zeichen gefunden: Bitte nur Ziffern oder "," oder "/" oder "%" benutzen.')
            )
            
class BulkField(forms.CharField):
    
    allowed_chars = [',', '/', '%', '-', '*']
    
    
    def __init__(self, required=False, allowed_chars=None, 
                #validators=[validate_bulkfield], 
                *args, **kwargs):
        super(BulkField, self).__init__(required=required,  *args, **kwargs)
        self.allowed_chars = allowed_chars or self.allowed_chars
        msg_text = 'Unerlaubte Zeichen gefunden: Bitte nur Ziffern'
        msg_text += ' oder ' if self.allowed_chars else ''
        msg_text += ' oder '.join(['"'+s+'"' for s in self.allowed_chars]) + ' benutzen.'
        self.error_messages['invalid'] = _(msg_text)
        
    def widget_attrs(self, widget):
        attrs = super(BulkField, self).widget_attrs(widget)
        attrs['style'] = 'width:350px;'
        return attrs
        
    def validate(self, value):
        super(BulkField, self).validate(self)
        for char in value:
            if not char.isspace() and not char.isnumeric() and not char in self.allowed_chars:
                raise ValidationError(self.error_messages['invalid'], code='invalid')
                print('ValidationError')
                raise ValidationError(
                    _('Unerlaubte Zeichen gefunden: Bitte nur Ziffern oder "," oder "/" oder "%" benutzen.')
                )
        
    def clean(self, value):
        value = super(BulkField, self).clean(value)
        value = value.strip()
        if value and value[-1] in self.allowed_chars:
            # Strip accidental last delimiter
            value = value[:-1]
        return value
        
    def to_list(self, value):
        if not value:
            return [], 0
        temp = []
        item_count = 0
        for item in value.split(','):
            item = item.strip()
            if item:
                if item.count('-')==1:
                    if item.count("*") == 1:
                        item,  multi = item.split("*")
                        multi = int(multi)
                    else:
                        multi = 1
                    s, e = (int(i) for i in item.split("-"))
                    
                    for i in range(s, e+1, multi):
                        temp.append([str(i+j) for j in range(multi)])
                        item_count += 1
                elif '/' in item:
                    temp.append([i for i in item.split('/') if i])
                    item_count += 1
                else:
                    temp.append(item)
                    item_count += 1
        return temp, item_count
        
class BulkJahrField(BulkField):
    
    allowed_chars = [',', '/']
    
    def clean(self, value):
        # Normalize Jahr values into years seperated by commas only
        # Also correct the year if year is a shorthand
        value = super(BulkJahrField, self).clean(value)
        clean_values = []
        for item in value.replace('/', ',').split(','):
            item = item.strip()
            if len(item)==2:
                if int(item) <= 17:
                    item = '20' + item
                else:
                    item = '19' + item
            clean_values.append(item)
        return ','.join(clean_values)
        
    def to_list(self, value):
        temp, item_count = super(BulkJahrField, self).to_list(value)
        return temp, 0

class BulkForm(forms.Form):
    
    model = None
    total_count = 0
    split_data = {} 
    _row_data = []
    each_fields = set() # data of these fields are part of every row
    at_least_one_required = [] # at least one of these fields needs to be filled out
    
    help_text = "BEEP BOOP"
    
    fieldsets = [
        (None, {'fields':[]}), 
        ('Mindestes eines dieser Feld ausfüllen', {'fields':[]}), 
    ]
    
    def __init__(self, *args, **kwargs):
        super(BulkForm, self).__init__(*args, **kwargs)
        self.each_fields = set(kwargs.get('each_fields', []))
        for fld_name, fld in self.fields.items():
            if isinstance(fld, BulkField):
                if isinstance(fld, BulkJahrField):
                    self.each_fields.add(fld_name)
                continue
            else:
                self.each_fields.add(fld_name)
        self.fieldsets[0][1]['fields'] = [fld_name for fld_name in self.fields if fld_name not in self.at_least_one_required]
        self.fieldsets[1][1]['fields'] = self.at_least_one_required
        

    class Media:
        css = {
            'all' : ('admin/css/forms.css', )
        }
        extra = '' if settings.DEBUG else '.min'
        js = [
            'admin/js/vendor/jquery/jquery%s.js' % extra,
            'admin/js/jquery.init.js',
            'admin/js/collapse%s.js' % extra,
        ]
            
    @property
    def media(self):
        media = super(BulkForm, self).media # Base + Widget Media
        for fieldset in self.__iter__():
            media += fieldset.media         # Fieldset Media
        return media
        
    def has_changed(self):
        """
        Returns True if data differs from initial.
        """
        has_changed = bool(self.changed_data)
        if has_changed:
            self._row_data = []
        return has_changed
        
    def clean(self):
        errors = False
        self.split_data = {}
        for fld_name, fld in self.fields.items():
            if hasattr(fld, 'to_list'):
                list_data, item_count = fld.to_list(self.cleaned_data.get(fld_name))
                if item_count and self.total_count and item_count != self.total_count:
                    errors = True
                else:
                    if list_data:
                        self.split_data[fld_name]=list_data
                    if item_count and not fld_name in self.each_fields:
                        self.total_count = item_count
        if errors:
            raise ValidationError('Ungleiche Anzahl an {}.'.format(self.model._meta.verbose_name_plural))
        if all(len(self.split_data.get(fld_name, []))==0 for fld_name in self.at_least_one_required):
            raise ValidationError('Bitte mindestens eines dieser Felder ausfüllen: {}'.format(
                    ", ".join([self.fields.get(fld_name).label or fld_name for fld_name in self.at_least_one_required])
                ))
      
    def clean_lagerort(self):
        if not self.cleaned_data['lagerort']:
            self.cleaned_data['lagerort'] = lagerort.objects.get(pk=ZRAUM_ID)
        return self.cleaned_data['lagerort']
            
    def clean_dublette(self):
        if not self.cleaned_data['dublette']:
            self.cleaned_data['dublette'] = lagerort.objects.get(pk=DUPLETTEN_ID)
        return self.cleaned_data['dublette']

    @property
    def row_data(self):
        # NOTE: this doesn't verify that the form has been cleaned and that split_data is populated..
        if not self._row_data or self.has_changed():
            from collections import OrderedDict
            for c in range(self.total_count):
                row = OrderedDict()
                for fld_name in self.field_order:
                    if fld_name in self.split_data:
                        if fld_name in self.each_fields:
                            # all items of this list are part of this row
                            item = self.split_data.get(fld_name)
                        else:
                            # only one item of this list needs to be part of this row
                            item = self.split_data.get(fld_name)[c]
                    else:
                        item = self.cleaned_data.get(fld_name)
                    if item:
                        if not isinstance(item, list):
                            # Force items to be a list, since we're checking for len(item) in the view..
                            item = [item]
                        row[fld_name] = item
                row['instance'] = self.lookup_instance(row).first()
                if row['instance']:
                    #two (or more) rows might be related to a single already existing instance
                    if any(row['instance']==other_row['instance'] for other_row in self._row_data):
                        continue
                    #TODO: Replace row_data with the data of the instance?
                    
                    row['lagerort'] = [self.cleaned_data['dublette']]
                else:
                    row['lagerort'] = [self.cleaned_data['lagerort']]
                    
                self._row_data.append(row)
        return self._row_data
        
    
    def __iter__(self):
        fieldsets = getattr(self, 'fieldsets', [(None, {'fields':list(self.fields.keys())})])
            
        from django.contrib.admin.helpers import Fieldset
        for name, options in fieldsets:
            yield Fieldset(
                self, name,
                **options
            )
            
            
class BulkFormAusgabe(BulkForm):
    model = ausgabe
    field_order = ['magazin', 'jahrgang', 'jahr', 'num', 'monat', 'lnum', 'audio', 'lagerort']
    at_least_one_required = ['num', 'monat', 'lnum']
    
    
    magazin = forms.ModelChoiceField(required = True, 
                                    queryset = magazin.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmagazin'))
                                    
    jahrgang = forms.IntegerField(required = False, min_value = 1) 
    
    jahr = BulkJahrField(required = True, label = 'Jahr')
    num = BulkField(label = 'Nummer')
    monat = BulkField(label = 'Monate')
    lnum = BulkField(label = 'Laufende Nummer')
    
    audio = forms.BooleanField(required = False, label = 'Musik Beilage:')
    lo = lagerort
    lagerort = forms.ModelChoiceField(required = False, 
                                    queryset = lo.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'), 
                                    initial = ZRAUM_ID)
    dublette = forms.ModelChoiceField(required = False, 
                                    queryset = lo.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'), 
                                    initial = DUPLETTEN_ID, 
                                    label = 'Lagerort f. Dubletten')
    
    def row_data_lagerort(self, row):
        if self.lookup_instance(row).exists():
            return lagerort.objects.get(pk=DUPLETTEN_ID)
        return lagerort.objects.get(pk=ZRAUM_ID)
        
    def lookup_instance(self, row):
        qs = self.cleaned_data.get('magazin').ausgabe_set
        
        for fld_name, row_data in row.items():
            if fld_name in ['jahrgang', 'lagerort', 'magazin', 'audio']:
                continue
            x = 'ausgabe_{}'.format(fld_name)
            x += '__{}'.format(fld_name if fld_name != 'monat' else 'monat_id')
            if isinstance(row_data, str):
                row_data = [row_data]
            for value in row_data:
                if value:
                    qs = qs.filter(**{x:value})
        if qs.count()>1:
            print("WARNING : multiple results found for: {}".format(row))
        return qs
        
test_data = dict(magazin=tmag.pk, jahr='10,11', num='1-10*3', monat='1,2,3,4', audio=True, lagerort = ZRAUM_ID)
test_form = BulkFormAusgabe(test_data)
