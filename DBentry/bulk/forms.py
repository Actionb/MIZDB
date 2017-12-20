
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from DBentry.forms import MIZAdminForm
from DBentry.models import ausgabe, magazin, lagerort, provenienz
from DBentry.constants import ATTRS_TEXTAREA, DUPLETTEN_ID, ZRAUM_ID
from .fields import *

from dal import autocomplete


class BulkForm(MIZAdminForm):
    
    model = None
    each_fields = set() # data of these fields are part of every row
    at_least_one_required = [] # at least one of these fields needs to be filled out
    
    help_text = ''
    #TODO: add help text to fieldsets, remember to also update the template for this
    fieldsets = [
        ('Angaben dieser Felder werden jedem Datensatz zugewiesen', {'fields':[]}), 
        ('Mindestes eines dieser Feld ausfüllen', {'fields':[]}), 
    ]
    
    
    def __init__(self, *args, **kwargs):
        super(BulkForm, self).__init__(*args, **kwargs)
        self.each_fields = set(kwargs.get('each_fields', []))
        self._row_data = []
        self.total_count = 0
        self.split_data = {} 
        for fld_name, fld in self.fields.items():
            if isinstance(fld, BulkField):
                if isinstance(fld, BulkJahrField):
                    self.each_fields.add(fld_name)
                continue
            else:
                self.each_fields.add(fld_name)
        self.fieldsets[0][1]['fields'] = [fld_name for fld_name in self.fields if fld_name not in self.at_least_one_required]
        self.fieldsets[1][1]['fields'] = self.at_least_one_required
        
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
            
            
class BulkFormAusgabe(BulkForm):
    model = ausgabe
    field_order = ['magazin', 'jahrgang', 'jahr', 'status', 'info', 'audio', 'audio_lagerort', 'lagerort', 'dublette', 'provenienz']
    preview_fields = ['magazin', 'jahrgang', 'jahr', 'num', 'monat', 'lnum', 'audio', 'audio_lagerort', 'lagerort']
    at_least_one_required = ['num', 'monat', 'lnum']
    multiple_instances_error_msg = "Es wurden mehrere passende Ausgaben gefunden. Es kann immer nur eine bereits bestehende Ausgabe verändert werden."
    
    
    magazin = forms.ModelChoiceField(required = True, 
                                    queryset = magazin.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmagazin'))
                                    
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
                                    widget = autocomplete.ModelSelect2(url='aclagerort'))
    lagerort = forms.ModelChoiceField(required = False, 
                                    queryset = lo.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'), 
                                    initial = ZRAUM_ID, 
                                    label = 'Lagerort f. Ausgaben')
    dublette = forms.ModelChoiceField(required = False, 
                                    queryset = lo.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'), 
                                    initial = DUPLETTEN_ID, 
                                    label = 'Lagerort f. Dubletten')
    provenienz = forms.ModelChoiceField(required = False, 
                                    queryset = provenienz.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='acprov'))    
    info = forms.CharField(required = False, widget = forms.Textarea(attrs=ATTRS_TEXTAREA), label = 'Bemerkungen')
    
    status = forms.ChoiceField(choices = ausgabe.STATUS_CHOICES, initial = 1, label = 'Bearbeitungsstatus')
                             
    def clean(self):
        super(BulkFormAusgabe, self).clean()
        if self.cleaned_data['audio'] and not self.cleaned_data['audio_lagerort']:
            raise ValidationError('Bitte einen Lagerort für die Musik Beilage angeben.')
      
    def clean_lagerort(self):
        if not self.cleaned_data['lagerort']:
            self.cleaned_data['lagerort'] = lagerort.objects.get(pk=ZRAUM_ID)
        return self.cleaned_data['lagerort']
            
    def clean_dublette(self):
        if not self.cleaned_data['dublette']:
            self.cleaned_data['dublette'] = lagerort.objects.get(pk=DUPLETTEN_ID)
        return self.cleaned_data['dublette']
    
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
    
    def row_data_lagerort(self, row):
        if self.lookup_instance(row).exists():
            return lagerort.objects.get(pk=DUPLETTEN_ID)
        return lagerort.objects.get(pk=ZRAUM_ID)
        
    def lookup_instance(self, row):
        qs = self.cleaned_data.get('magazin').ausgabe_set
        
        for fld_name, row_data in row.items():
            if not fld_name in ['jahr', 'num', 'monat', 'lnum']:
                continue
            x = 'ausgabe_{}'.format(fld_name)
            x += '__{}'.format(fld_name if fld_name != 'monat' else 'monat_id')
            if isinstance(row_data, str):
                row_data = [row_data]
            for value in row_data:
                if value:
                    qs = qs.filter(**{x:value})                
        return qs
        
    @property
    def row_data(self):
        # NOTE: this doesn't verify that the form has been cleaned and that split_data is populated..
        if not self._row_data or self.has_changed():
            for c in range(self.total_count):
                row = {}
                for fld_name, fld in self.fields.items():
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
                    # lookup_instance returned multiple instances/objects
                    row['multiples'] = qs
                    
                self._row_data.append(row)
        return self._row_data
