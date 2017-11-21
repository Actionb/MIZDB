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
                                    
    'bland' : dict(required = False, 
                                    label = "Bundesland", 
                                    queryset = bundesland.objects.all(),  
                                    widget = autocomplete.ModelSelect2(url='acbland', forward=['land'], 
                                                attrs = {'data-placeholder': 'Bitte zuerst ein Land auswählen!'}),
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
    
def advSF_factory_old(model_admin, labels = {}, formfield_class = {}):
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
    
from DBentry.ac.urls import patterns_by_model
def advSF_factory(model_admin, labels = {}, formfield_classes = {}):
    """
    Handles the creation of all the autocomplete formfields.
    """
    model = model_admin.model
    attrs = {}
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})
    
    for field_path in asf_dict.get('selects', {}):
        rel_or_field = get_fields_from_path(model, field_path)[-1]

        if not rel_or_field.is_relation:
            # Let the template/the tag deal with the non-relation (choice) selects
            continue
        field = rel_or_field.get_path_info()[-1].join_field
        if field.name in FORMFIELDS:
            formfield_opts = FORMFIELDS[field.name].copy()
        else:
            formfield_opts = dict(required = False)
            formfield_opts['label'] = labels.get(field_path, None) or field.formfield().label
            formfield_opts['queryset'] = field.related_model._default_manager
            
            url = ''
            for pattern in patterns_by_model(field.related_model):
                if 'create_field' not in pattern.callback.view_initkwargs:
                    url = pattern.name
                    break
            if url:
                if rel_or_field.many_to_many:
                    formfield_opts['widget'] = autocomplete.ModelSelect2Multiple(url)
                else:
                    formfield_opts['widget'] = autocomplete.ModelSelect2(url)
            
        formfield_class = formfield_classes.get(field_path, None) or forms.ModelChoiceField #? or field.formfield()
        attrs[field_path] = formfield_class(**formfield_opts)
    return type('AdvSF'+model.__name__, (AdvSFForm, ), attrs )
