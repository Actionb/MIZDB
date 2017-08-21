from django import forms
from django.forms import modelform_factory, Textarea

from .models import *
from .constants import *

from dal import autocomplete

FORMFIELDS = {
    'ausgabe' : forms.ModelChoiceField(required = False, 
                                    queryset = ausgabe.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='acausgabe', forward = ['ausgabe__magazin'], 
                                                attrs = {'data-placeholder': 'Bitte zuerst ein Magazin auswählen!'})
                                    ), 
                                    
    'autor' : forms.ModelChoiceField(required = False, 
                                    label = "Autor", 
                                    queryset = autor.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acautor'), 
                                    ), 
                                    
    'band' : forms.ModelChoiceField(required = False, 
                                    label = "Band", 
                                    queryset = band.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acband_nocreate'), 
                                    ), 
                                    
    'genre' : forms.ModelChoiceField(required = False, 
                                    label = "Genre", 
                                    queryset = genre.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acgenre_nocreate'), 
                                    ),
                                    
    'herkunft' : forms.ModelChoiceField(required = False, 
                                        label = "Herkunftsort", 
                                        queryset = ort.objects.all(),  
                                        widget = autocomplete.ModelSelect2(url='acort', forward=['person__herkunft__land']), 
                                        ), 
                                        
    'instrument' : forms.ModelChoiceField(required = False, 
                                    label = "Instrument", 
                                    queryset = instrument.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acinstrument_nocreate'), 
                                    ), 
                                     
    'land' : forms.ModelChoiceField(required = False, 
                                    label = "Herkunftsland", 
                                    queryset = land.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acland_nocreate'), 
                                    ),
                                    
    'magazin' : forms.ModelChoiceField(required = False, 
                                    label = "Magazin", 
                                    queryset = magazin.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmagazin_nocreate'), 
                                    ), 
                                    
    'musiker' : forms.ModelChoiceField(required = False, 
                                    label = "Mitglied", 
                                    queryset = musiker.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmusiker_nocreate'), 
                                    ), 
                                    
    'person' : forms.ModelChoiceField(required = False, 
                                    label = "Person", 
                                    queryset = person.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acperson'), 
                                    ),  
                                    
    'schlagwort' : forms.ModelChoiceField(required = False, 
                                    label = "Schlagwort", 
                                    queryset = schlagwort.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acschlagwort_nocreate'), 
                                    ), 
                                    
}
class AdvSFForm(forms.Form):
    
    def as_div(self):
        "Returns this form rendered as HTML <div>s."
        return self._html_output(
            normal_row="""
            <span>
            <div>%(label)s</div>
            <div>%(field)s%(help_text)s</div>
            </span>
            """, 
            error_row='%s',
            row_ender='</div>',
            help_text_html=' <span class="helptext">%s</span>',
            errors_on_separate_row=True)
    
def advSF_factory(model_admin):
    model = model_admin.model
    opts = model_admin.opts
    from collections import OrderedDict
    attrs = OrderedDict()
    
    asf_dict = getattr(model_admin, 'advanced_search_form', dict())
    from itertools import chain
    formfield_names = [i for i in chain(*asf_dict.values())]
    for formfield_name in formfield_names:
        fld_name = formfield_name.split("__")[-1]
        if fld_name in FORMFIELDS:
            attrs[formfield_name] = FORMFIELDS[fld_name]
    return type('AdvSF'+model.__name__, (AdvSFForm, ), attrs )
