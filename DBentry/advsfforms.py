from django import forms
from django.contrib.admin.utils import get_fields_from_path

from .models import *
from .constants import *

from dal import autocomplete

FORMFIELDS = {
    'ausgabe' : dict(required = False, 
                                    label = 'Ausgabe', 
                                    queryset = ausgabe.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='acausgabe', forward = ['ausgabe__magazin'], 
                                                attrs = {'data-placeholder': 'Bitte zuerst ein Magazin auswählen!'}), 
                                    ), 
                                    
    'autor' : dict(required = False, 
                                    label = "Autor", 
                                    queryset = autor.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acautor'), 
                                    ), 
                                    
    'band' : dict(required = False, 
                                    label = "Band", 
                                    queryset = band.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acband_nocreate'), 
                                    ), 
                                    
    'bland' : dict(required = False, 
                                    label = "Bundesland", 
                                    queryset = bundesland.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acbland', forward=['land'], 
                                                attrs = {'data-placeholder': 'Bitte zuerst ein Land auswählen!'}),
                                    ), 
                                    
    'genre' : dict(required = False, 
                                    label = "Genre", 
                                    queryset = genre.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acgenre_nocreate'), 
                                    ),
                                    
    'herkunft' : dict(required = False, 
                                        label = "Herkunftsort", 
                                        queryset = ort.objects.all(), 
                                        widget = autocomplete.ModelSelect2(url='acort'), 
                                        ), 
                                        
    'instrument' : dict(required = False, 
                                    label = "Instrument", 
                                    queryset = instrument.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acinstrument_nocreate'), 
                                    ), 
    
    'lagerort' : dict(required = False, 
                                    label = "Lagerort", 
                                    queryset = lagerort.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='aclagerort'), 
                                    ),
                                     
    'land' : dict(required = False, 
                                    label = "Land", 
                                    queryset = land.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acland_nocreate'), 
                                    ),
                                    
    'magazin' : dict(required = False, 
                                    label = "Magazin", 
                                    queryset = magazin.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmagazin_nocreate'), 
                                    ), 
                                    
    'musiker' : dict(required = False, 
                                    label = "Musiker", 
                                    queryset = musiker.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acmusiker_nocreate'), 
                                    ), 
                                    
    'ort' : dict(required = False, 
                                        label = "Ort", 
                                        queryset = ort.objects.all(),  
                                        widget = autocomplete.ModelSelect2(url='acort'), 
                                        ), 
                                    
    'person' : dict(required = False, 
                                    label = "Person", 
                                    queryset = person.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acperson'), 
                                    ),  
                                    
    'schlagwort' : dict(required = False, 
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
    
def advSF_factory(model_admin, labels = {}, formfield_class = {}):
    #TODO: allow overriding some attrs (label) of formfields not present in FORMFIELDS
    # e.g. those formfields that are not going to be DAL and just simply default selects
    model = model_admin.model
    attrs = {}
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})
    from itertools import chain
    formfield_names = [i for i in chain(*asf_dict.values())] #NOTE: shouldnt we exclude the asf_dict labels from the chain?
    for formfield_name in formfield_names:
        fld_name = formfield_name.split("__")[-1]
        if not fld_name in FORMFIELDS:
            # Usually the name of the fld is related to its related model (a field related to 'land' is called 'land')
            # but sometimes, I am smart and name the field differently ('sitz' of verlag refers to land)
            try:
                fld_name = get_fields_from_path(model, formfield_name)[-1].related_model._meta.model_name
            except:
                continue
        if fld_name in FORMFIELDS:
            formfield_opts = FORMFIELDS[fld_name].copy()
            if formfield_name in labels:
                formfield_opts['label'] = labels[formfield_name]
            if formfield_name in formfield_class:
                attrs[formfield_name] = formfield_class[formfield_name](**formfield_opts)
            else:
                attrs[formfield_name] = forms.ModelChoiceField(**formfield_opts)
    return type('AdvSF'+model.__name__, (AdvSFForm, ), attrs )
