from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q

from DBentry.forms import MIZAdminForm, XRequiredFormMixin
from DBentry.models import ausgabe, magazin, lagerort, provenienz
from DBentry.constants import ATTRS_TEXTAREA, DUPLETTEN_ID, ZRAUM_ID
from DBentry.ac.widgets import make_widget
from .fields import BulkField, BulkJahrField

class BulkForm(MIZAdminForm):
    
    model = None
    
    # these fields are assigned to the first fieldset and data of these fields are part of every row/created object
    each_fields = set() 
    # fields for the second fieldset
    split_fields = () 
    
    fieldsets = [
        ('Angaben dieser Felder werden jedem Datensatz zugewiesen', {'fields':[]}), 
        ('Angaben dieser Felder werden aufgeteilt', {'fields':[]}), 
        (None, {'fields':[]}), 
    ]
    
    def __init__(self, *args, **kwargs):
        self._row_data = [] 
        self.total_count = 0 # the total count of objects to be created
        self.split_data = {} # a dictionary of {field names : split up values according to BulkField.to_list}
        
        super(BulkForm, self).__init__(*args, **kwargs)
                
        # Add the fields to the fieldsets, according to the order given by .fields (and thus given by field_order if available)
        self.fieldsets[0][1]['fields'] = [fld_name for fld_name in self.fields if fld_name in self.each_fields]
        self.fieldsets[1][1]['fields'] = [fld_name for fld_name in self.fields if fld_name in self.split_fields]

        
    @property
    def row_data(self):
        return self._row_data
        
    def has_changed(self):
        """
        Returns True if data differs from initial.
        """
        has_changed = bool(self.changed_data)
        if has_changed:
            # Reset _row_data
            self._row_data = []
        return has_changed
        
    def clean(self):
        """
        Populate split_data with data from BulkFields and raises errors if an unequal amount of data or missing required data is encountered.
        """
        cleaned_data = super().clean()
        if self._errors:
            # Other cleaning methods have added errors, stop further cleaning
            return cleaned_data
            
        self.split_data = {}
        for fld_name, fld in self.fields.items():
            if isinstance(fld, BulkField):
                # Retrieve the split up data and the amount of objects that are expected to be created with that data
                list_data, item_count = fld.to_list(cleaned_data.get(fld_name))
                # If the field belongs to the each_fields group, we should ignore the item_count it is returning as its data is used for every object we are about to create
                if not fld_name in self.each_fields and item_count and self.total_count and item_count != self.total_count:
                    # This field's data exists and is meant to be split up into individual items, but the amount of items differs from the previously determined total_count
                    self.add_error(fld_name, 'Ungleiche Anzahl an {}.'.format(self.model._meta.verbose_name_plural))
                else:
                    # Either:
                    # - the field is an each_field
                    # - its item_count is zero
                    # - no total_count has yet been determined (meaning this is the first field encountered that contains list_data)
                    if list_data:
                        self.split_data[fld_name]=list_data
                    if item_count and not fld_name in self.each_fields:
                        # The item_count is not zero,  total_count IS zero (not yet calculated) and the field is eligible (by virtue of being a non-each_fields BulkField) to set the total_count
                        # All subsequent BulkField's item_counts in the iteration have to match this field's item_count (or be zero) or we cannot define the exact number of objects to create
                        self.total_count = item_count
        return cleaned_data
            
class BulkFormAusgabe(XRequiredFormMixin, BulkForm):
    # Form attributes
    model = ausgabe
    field_order = ['magazin', 'jahrgang', 'jahr', 'status', 'beschreibung', 'bemerkungen', 'audio', 'audio_lagerort', 'ausgabe_lagerort', 'dublette', 'provenienz']
    
    # BulkForm/XRequiredFormMixin attributes
    xrequired = [{'min':1, 'fields':['jahr', 'jahrgang']}, {'min':1, 'fields':['num', 'monat', 'lnum']}]   
    preview_fields = [
        'magazin', 'jahrgang', 'jahr', 'num', 'monat', 'lnum', 'audio', 'audio_lagerort', 
        'ausgabe_lagerort', 'provenienz'
    ]
    each_fields = [
        'magazin', 'jahrgang', 'jahr', 'audio', 'audio_lagerort', 'ausgabe_lagerort', 'dublette', 
        'provenienz', 'beschreibung', 'bemerkungen', 'status'
    ]
    split_fields = ['num', 'monat', 'lnum']
    
    # Field declarations
    magazin = forms.ModelChoiceField(required = True, 
                                    queryset = magazin.objects.all(),  
                                    widget = make_widget(model_name='magazin', wrap=True))
                                    
    jahrgang = forms.IntegerField(required = False, min_value = 1) 
    
    jahr = BulkJahrField(required = False, label = 'Jahr')
    num = BulkField(label = 'Nummer')
    monat = BulkField(label = 'Monate')
    lnum = BulkField(label = 'Laufende Nummer')
    
    audio = forms.BooleanField(required = False, label = 'Musik Beilage:')
    audio_lagerort = forms.ModelChoiceField(required = False, 
                                    label = 'Lagerort f. Musik Beilage', 
                                    queryset = lagerort.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True))
    ausgabe_lagerort = forms.ModelChoiceField(required = True, 
                                    queryset = lagerort.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True), 
                                    initial = ZRAUM_ID, 
                                    label = 'Lagerort f. Ausgaben')
    dublette = forms.ModelChoiceField(required = True, 
                                    queryset = lagerort.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True), 
                                    initial = DUPLETTEN_ID, 
                                    label = 'Lagerort f. Dubletten')
    provenienz = forms.ModelChoiceField(required = False, 
                                    queryset = provenienz.objects.all(), 
                                    widget = make_widget(model_name='provenienz', wrap=True))    
    beschreibung = forms.CharField(required = False, widget = forms.Textarea(attrs=ATTRS_TEXTAREA), label = 'Beschreibung')
    bemerkungen = forms.CharField(required = False, widget = forms.Textarea(attrs=ATTRS_TEXTAREA), label = 'Bemerkungen')
    
    status = forms.ChoiceField(choices = ausgabe.STATUS_CHOICES, initial = 1, label = 'Bearbeitungsstatus') 
        
    help_text = {
        'head' : """Dieses Formular dient zur schnellen Eingabe vieler Ausgaben.
                    Dabei gilt die Regel, dass allen Ausgaben dasselbe Jahr und derselbe Jahrgang zugewiesen werden. Es ist also nicht möglich, mehrere 'Jahrgänge' auf einmal einzugeben.
                    Liegt allen Ausgaben eine Musik-CD, o.ä. bei, setze den Haken bei dem Feld 'Musik-Beilage'. Ein Datensatz entsprechend dem Titel "Musik-Beilage: <Name des Magazins> <Name der Ausgabe>" wird dann in der Audiotabelle erstellt und mit der jeweiligen Ausgabe verknüpft.
                    
                    Mit den Auswahlfeldern zu Lagerort und Dublettenlagerort kann festgelegt werden, wo diese Ausgaben (und eventuelle Dubletten) gelagert werden.
                    Sollte eine der im Formular angegebenen Ausgaben bereits einen Bestand in der Datenbank haben, so wird automatisch ein Dublettenbestand hinzugefügt und die vorhandene Ausgabe erscheint im Vorschau-Bereich 'Bereits vorhanden'. Bitte kontrolliert die Korrektheit eurer Angaben, sollte dies der Fall sein.
                    
                    Monate bitte als Nummern angeben und Leerzeichen vermeiden!
                    
                    In der Vorschau könnt ihr die resultierenden Ausgaben eurer Angaben überprüfen.
                    WICHTIG: Es wird abgespeichert was in dem Formular steht, nicht was in der Vorschau gezeigt wird! Erstellt ihr eine Vorschau zu einer Reihe von Angaben und ändert dann die Angaben wieder, werden die gespeicherten Ausgaben NICHT der Vorschau entsprechen.
                    Es ist also am besten, immer erst eine Vorschau nach jeder Änderung zu erstellen und danach abzuspeichern!
                    
                    Erlaubte Zeichen: """, 
                    
        'list_items' : [
                (' "," (Trennzeichen)' ,  'Ein Komma trennt einzelne Gruppierungen von Angaben voneinander: 1,3,6-8 = 1,3,6,7,8'), 
                (' "-" (von bis)' ,  'Das Minus-Zeichen stellt eine Reihe von Angaben dar: 1-4 = 1,2,3,4'), 
                (' "/" (einfache Gruppierung)' , 'Das Slash-Zeichen weist einer einzelnen Ausgabe mehrere Angaben zu: 1,3,6/7 = 1,3,6 UND 7'), 
                (' "*" (mehrfache Gruppierung)' , 'Das Sternchen erlaubt Zuweisung mehrerer Angaben zu einer Reihe (Kombination von "-" und "/"): 1-4*2 = 1/2, 3/4 oder 1-6*3 = 1/2/3, 4/5/6'), 
            ], 
            
        'foot' : """
        Beispiele:
        Eine Ausgabe mit der Nummer 6 und den Monaten April und Mai:
        Nummer-Feld: 6
        Monat-Feld: 4/5
        
        Zwei Ausgaben mit den laufenden Nummern 253 und 255:
        Laufende Nummer: 253, 255
        
        Drei Ausgaben mit Nummern 3 bis 5 und Monaten Januar/Februar und März/April und Mai/Juni:
        Nummer: 3-5 (oder natürlich auch 3,4,5)
        Monat: 1-6*2 (oder auch 1/2, 3/4, 5/6)
        
        Ein ganzer Jahrgang von 11 Ausgaben mit Monaten Jan bis Dez, wobei im Juli und August eine zwei-monatige Ausgabe erschienen ist:
        Monat: 1-6, 7/8, 9-12 (oder auch 1,2,3,4,5,6,7/8,9,10,11,12)
        
        Eine jahresübergreifende Ausgabe mit dem Monat Dezember im Jahre 2000 und dem Monat Januar im Jahre 2001:
        Jahr: 2000,2001 (oder 2000/2001)
        Monat: 12/1
        """
    }
         
    def clean(self):
        # If the user wishes to add audio data to the objects they are creating, they MUST also define a lagerort for the audio
        if self.cleaned_data.get('audio') and not self.cleaned_data.get('audio_lagerort'):
            self.add_error('audio_lagerort', 'Bitte einen Lagerort für die Musik Beilage angeben.')
        return super().clean()
            
    def clean_monat(self):
        # Complain about monat values that are not in 1-12
        value = self.fields['monat'].widget.value_from_datadict(self.data, self.files, self.add_prefix('monat'))
        list_data, _ = self.fields['monat'].to_list(value)
        for _list in list_data.copy():
            if not isinstance(_list, list):
                _list = [_list]
            if any(int(v) < 1 or int(v) > 12 for v in _list):
                raise ValidationError('Monat-Werte müssen zwischen 1 und 12 liegen.')
        return value
        
    def lookup_instance(self, row):
        """
        For given data of a row, apply queryset filtering to find a matching instance.
        """
        qs = self.cleaned_data.get('magazin').ausgabe_set.all()
                
        for fld_name, field_path in [
            ('num', 'ausgabe_num__num'), 
            ('lnum', 'ausgabe_lnum__lnum'), 
            ('monat', 'ausgabe_monat__monat__ordinal')]: 
            row_data = row.get(fld_name, [])
            if isinstance(row_data, str):
                row_data = [row_data]
            for value in row_data:
                if value:
                    qs = qs.filter(**{field_path:value})
                    
        if not qs.exists():
            return qs
            
        jg = row.get('jahrgang', None)
        jahre = row.get('jahr', None)
        if isinstance(jahre, str): jahre = [jahre]
        
        if jg and jahre:
            if qs.filter(jahrgang = jg, ausgabe_jahr__jahr__in = jahre).exists():
                qs = qs.filter(jahrgang = jg, ausgabe_jahr__jahr__in = jahre)
            else:
                # Do not shadow possible duplicates that only have one of (jg, jahre) by using OR
                qs = qs.filter(Q(('jahrgang', jg)) | Q(('ausgabe_jahr__jahr__in', jahre)))
        elif jg:
            qs = qs.filter(jahrgang=jg)
        elif jahre:
            qs = qs.filter(ausgabe_jahr__jahr__in=jahre)
        return qs.distinct()
        
    @property
    def row_data(self):
        if self.is_valid():
            # form is valid, split_data has been populated in clean()
            if self.has_changed() or not self._row_data:
                for c in range(self.total_count):
                    row = {}
                    for fld_name, fld in self.fields.items():
                        if fld_name not in self.each_fields + self.split_fields:
                            # This field was not assigned to either each_fields or split_fields, ignore it
                            continue
                        if fld_name in self.split_data:
                            # this field is a BulkField
                            if fld_name in self.each_fields:
                                # all items of this list are part of this row
                                item = self.split_data.get(fld_name)
                            else:
                                # only one item of this list needs to be part of this row
                                item = self.split_data.get(fld_name)[c]
                        else:
                            item = self.cleaned_data.get(fld_name)
                        if item:
                            row[fld_name] = item
                            
                    qs = self.lookup_instance(row)
                    row['ausgabe_lagerort'] = self.cleaned_data['ausgabe_lagerort']
                    if qs.count()==0:
                        # No ausgabe fits the parameters: we are creating a new one
                        
                        # See if this row (in its exact form) has already appeared in _row_data
                        # We do not want to create multiple objects with the same data,
                        # instead we will mark this row as a duplicate of the first matching row found
                        # By checking for row == row_dict we avoid 'nesting' duplicates.
                        for row_dict in self._row_data:
                            if row == row_dict:
                                row['ausgabe_lagerort'] = self.cleaned_data['dublette']
                                row['dupe_of'] = row_dict
                                break
                    elif qs.count()==1:
                        # A single object fitting the parameters already exists: this row represents a duplicate of that object.
                        
                        row['instance'] = qs.first()
                        row['ausgabe_lagerort'] = self.cleaned_data['dublette']
                    else:
                        # lookup_instance returned multiple instances/objects, this row will be ignored from now on
                        row['multiples'] = qs
                        
                    self._row_data.append(row)
        return self._row_data
