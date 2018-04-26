
from django.core.exceptions import ValidationError

from dal import autocomplete

from DBentry.forms import MIZAdminForm
from DBentry.models import ausgabe, magazin, lagerort, provenienz
from DBentry.constants import ATTRS_TEXTAREA, DUPLETTEN_ID, ZRAUM_ID
from DBentry.ac.widgets import make_widget
from .fields import *

class BulkForm(MIZAdminForm):
    
    model = None
    each_fields = set() # data of these fields are part of every row/created object
    at_least_one_required = [] # at least one of these fields needs to be filled out, takes priority over each_fields in regards to in which fieldset the fields will end up in
    

    help_text = ''
    #TODO: add help text to fieldsets, remember to also update the template for this
    fieldsets = [
        ('Angaben dieser Felder werden jedem Datensatz zugewiesen', {'fields':[]}), 
        ('Mindestes eines dieser Feld ausfüllen', {'fields':[]}), 
        (None, {'fields':[]}), 
    ]
    
    def __init__(self, *args, **kwargs):
        # Combine declared at_least_one_required/each_fields with those passed in and remove duplicate entries
        self.at_least_one_required = set(list(self.at_least_one_required) + list(kwargs.pop('at_least_one_required', [])) )
        self.each_fields = set(list(self.each_fields) + list(kwargs.pop('each_fields', [])) )
        self._row_data = [] # this needs to be here in init or row_data will magically inherit data from previous instances?!
        self.total_count = 0 # the total count of objects to be created
        self.split_data = {} # a dictionary of field names : split up values according to BulkField.to_list
        
        super(BulkForm, self).__init__(*args, **kwargs)
        # For lazy people: walk through the fields and add any non-BulkField to the each_fields list and any BulkFields to the at_least_one_required list
        for fld_name, fld in self.fields.items():
            if isinstance(fld, BulkField):
                if isinstance(fld, BulkJahrField):
                    # Of the BulkFields only BulkJahrField should be used in an each_field role
                    self.each_fields.add(fld_name)
            else:
                self.each_fields.add(fld_name)
                
        # Remove any fields from self.each_fields that are both in each_fields and at_least_one_required, as each_fields and at_least_one_required should be mutually exclusive
        self.each_fields = self.each_fields - (self.each_fields & self.at_least_one_required)
        # Find the fields that live neither in each_fields nor at_least_one_required (which can ONLY be regular BulkField fields at this point)
        # TODO: find a home for them!
        homeless_fields = set(self.fields.keys()) - self.each_fields - self.at_least_one_required
                
        # Add the fields to the fieldsets, according to the order given by .fields (and thus given by field_order if available)
        self.fieldsets[0][1]['fields'] = [fld_name for fld_name in self.fields if fld_name in self.each_fields]
        self.fieldsets[1][1]['fields'] = [fld_name for fld_name in self.fields if fld_name in self.at_least_one_required]
        self.fieldsets[2][1]['fields'] = [fld_name for fld_name in self.fields if fld_name in homeless_fields]
        
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
        for fld_name in self.at_least_one_required:
            if not cleaned_data.get(fld_name) in self.fields[fld_name].empty_values:
                # If any of the fields in at_least_one_required contain valid data, we're good
                break
        else:
            # otherwise mark the form as invalid
            raise ValidationError('Bitte mindestens eines dieser Felder ausfüllen: {}'.format(
                    ", ".join([self.fields.get(fld_name).label or fld_name for fld_name in self.at_least_one_required])
                ))   
        errors = False
        self.split_data = {}
        for fld_name, fld in self.fields.items():
            if isinstance(fld, BulkField):
                # Retrieve the split up data and the amount of objects that are expected to be created with that data
                list_data, item_count = fld.to_list(cleaned_data.get(fld_name))
                # If the field belongs to the each_fields group, we should ignore the item_count it is returning as its data is used for every object we are about to create
                if not fld_name in self.each_fields and item_count and self.total_count and item_count != self.total_count:
                    # This field's data exists and is meant to be split up into individual items, but the amount of items differs from the previously determined total_count
                    errors = True
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
        if errors:
            raise ValidationError('Ungleiche Anzahl an {}.'.format(self.model._meta.verbose_name_plural))
        return cleaned_data
            
class BulkFormAusgabe(BulkForm):
    
    model = ausgabe
    field_order = ['magazin', 'jahrgang', 'jahr', 'status', 'info', 'audio', 'audio_lagerort', 'lagerort', 'dublette', 'provenienz']
    preview_fields = ['magazin', 'jahrgang', 'jahr', 'num', 'monat', 'lnum', 'audio', 'audio_lagerort', 'lagerort', 'provenienz']
    at_least_one_required = ['num', 'monat', 'lnum']
    multiple_instances_error_msg = "Es wurden mehrere passende Ausgaben gefunden. Es kann immer nur eine bereits bestehende Ausgabe verändert werden."
    
    magazin = forms.ModelChoiceField(required = True, 
                                    queryset = magazin.objects.all(),  
                                    widget = make_widget(model_name='magazin', wrap=True))
                                    
    jahrgang = forms.IntegerField(required = False, min_value = 1) 
    
    jahr = BulkJahrField(required = True, label = 'Jahr')
    num = BulkField(label = 'Nummer')
    monat = BulkField(label = 'Monate')
    lnum = BulkField(label = 'Laufende Nummer')
    
    lo = lagerort
    audio = forms.BooleanField(required = False, label = 'Musik Beilage:')
    audio_lagerort = forms.ModelChoiceField(required = False, 
                                    label = 'Lagerort f. Musik Beilage', 
                                    queryset = lo.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True))
    lagerort = forms.ModelChoiceField(required = True, 
                                    queryset = lo.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True), 
                                    initial = ZRAUM_ID, 
                                    label = 'Lagerort f. Ausgaben')
    dublette = forms.ModelChoiceField(required = True, 
                                    queryset = lo.objects.all(), 
                                    widget = make_widget(model_name='lagerort', wrap=True), 
                                    initial = DUPLETTEN_ID, 
                                    label = 'Lagerort f. Dubletten')
    provenienz = forms.ModelChoiceField(required = False, 
                                    queryset = provenienz.objects.all(), 
                                    widget = make_widget(model_name='provenienz', wrap=True))    
    info = forms.CharField(required = False, widget = forms.Textarea(attrs=ATTRS_TEXTAREA), label = 'Bemerkungen')
    
    status = forms.ChoiceField(choices = ausgabe.STATUS_CHOICES, initial = 1, label = 'Bearbeitungsstatus')
                             
    def clean(self):
        try:
            cleaned_data = super(BulkFormAusgabe, self).clean()
        except ValidationError as e:
            raise e
        else:
            # If the user wishes to add audio data to the objects they are creating, they MUST also define a lagerort for the audio
            if cleaned_data.get('audio') and not cleaned_data.get('audio_lagerort'):
                raise ValidationError('Bitte einen Lagerort für die Musik Beilage angeben.')
            return cleaned_data
    
    help_text = {
        'head' : """Dieses Formular dient zur schnellen Eingabe vieler Ausgaben.
                    Dabei gilt die Regel, dass allen Ausgaben dasselbe Jahr und denselben Jahrgang zugewiesen werden. Es ist also nicht möglich, mehrere 'Jahrgänge' auf einmal einzugeben.
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
        Jahr: 2000,2001 (oder 2000/2001 oder 00,01 oder 00/01)
        Monat: 12/1
        """
    }
        
    def lookup_instance(self, row):
        """
        For given data of a row, apply queryset filtering to find a matching instance.
        """
        qs = self.cleaned_data.get('magazin').ausgabe_set
        
        for fld_name, field_path in [
            ('jahr', 'ausgabe_jahr__jahr'), 
            ('num', 'ausgabe_num__num'), 
            ('lnum', 'ausgabe_lnum__lnum'), 
            ('monat', 'ausgabe_monat__monat_id')]:
            row_data = row.get(fld_name, [])
            if isinstance(row_data, str):
                row_data = [row_data]
            for value in row_data:
                if value:
                    qs = qs.filter(**{field_path:value})
        return qs
        
    @property
    def row_data(self):
        if self.is_valid():
        # form is valid, split_data has been populated in clean()
            if self.has_changed() or not self._row_data:
                for c in range(self.total_count):
                    row = {}
                    for fld_name, fld in self.fields.items():
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
                    row['lagerort'] = self.cleaned_data['lagerort']
                    if qs.count()==0:
                        # No ausgabe fits the parameters: we are creating a new one
                        
                        # See if this row (in its exact form) has already appeared in _row_data
                        # We do not want to create multiple objects with the same data,
                        # instead we will mark this row as a duplicate of the first matching row found
                        # By checking for row == row_dict we avoid 'nesting' duplicates.
                        for row_dict in self._row_data:
                            if row == row_dict:
                                row['lagerort'] = self.cleaned_data['dublette']
                                row['dupe_of'] = row_dict
                                break
                    elif qs.count()==1:
                        # A single object fitting the parameters already exists: this row represents a duplicate of that object.
                        
                        row['instance'] = qs.first()
                        row['lagerort'] = self.cleaned_data['dublette']
                    else:
                        # lookup_instance returned multiple instances/objects, this row will be ignored from now on
                        row['multiples'] = qs
                        
                    self._row_data.append(row)
        return self._row_data
