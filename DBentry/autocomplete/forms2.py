from django import forms
from DBentry.models import *
from dal import autocomplete

WIDGETS = {
}

class ACBaseForm(forms.ModelForm):
    class Meta:
        fields = '__all__'

class ACAudio(ACBaseForm):
    class Meta:
        widgets  = { 'sender' : autocomplete.ModelSelect2(url='acsender'), 
                    'lagerort' : autocomplete.ModelSelect2(url='aclagerort'), 
        }

class ACAusgabe(ACBaseForm):
    class Meta:
        widgets  = { 'magazin' : autocomplete.ModelSelect2(url='acmagazin'), 
                    'provenienz' : autocomplete.ModelSelect2(url='acprov'), 
        }

class ACAutor(ACBaseForm):
    class Meta:
        widgets = { 'person' : autocomplete.ModelSelect2(url='acperson')}

class ACBand(ACBaseForm):
    class Meta:
        widgets = { 'herkunft' : autocomplete.ModelSelect2(url='acort'), 
        }
        
        
class ACBuchSerie(ACBaseForm):
    class Meta:
        widgets = { 'buch_serie' : autocomplete.ModelSelect2(url='acbuchserie')}
        
class ACGenre(ACBaseForm):
    class Meta:
        widgets = { 'genre' : autocomplete.ModelSelect2(url='acgenre')}
        
class ACInstrument(ACBaseForm):
    class Meta:
        widgets = { 'instrument' : autocomplete.ModelSelect2(url='acinstrument')}
        
class ACMagazin(ACBaseForm):
    class Meta:
        widgets = { 'magazin' : autocomplete.ModelSelect2(url='acmagazin')}
   
class ACKreis(ACBaseForm):
    class Meta:
        widgets = { 'kreis' : autocomplete.ModelSelect2(url='ackreis')}
        
class ACLagerort(ACBaseForm):
    class Meta:
        widgets = { 'lagerort' : autocomplete.ModelSelect2(url='aclagerort')}
        
class ACLand(ACBaseForm):
    class Meta:
        widgets = { 'land' : autocomplete.ModelSelect2(url='acland')}
        
class ACMonat(ACBaseForm):
    class Meta:
        widgets = { 'monat' : autocomplete.ModelSelect2(url='acmonat')}

class ACMusiker(ACBaseForm):
    class Meta:
        widgets = { 'musiker' : autocomplete.ModelSelect2(url='acmusiker'), 
        }
        
class ACOrt(ACBaseForm):
    class Meta:
        widgets = { 'bland' : autocomplete.ModelSelect2(url='acbland'), 
                    'land' : autocomplete.ModelSelect2(url='acland'), 
        }
        
class ACperson(ACBaseForm):
#    autor = forms.ModelMultipleChoiceField(
#        queryset = autor.objects.all(), 
#        widget = autocomplete.ModelSelect2Multiple(url="acautor")
#    )
    class Meta:
        widgets = { 'herkunft' : autocomplete.ModelSelect2(url='acort')}
        
class ACSchlagwort(ACBaseForm):
    class Meta:
        widgets = { 'schlagwort' : autocomplete.ModelSelect2(url='acschlagwort')}
        
        
# ==================================================== Ort =============================================================


class ACBland(ACBaseForm):
    class Meta:
        widgets = { 'land' : autocomplete.ModelSelect2(url='acland')}
 
