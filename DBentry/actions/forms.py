
from collections import OrderedDict

from django import forms
from django.contrib.admin.utils import get_fields_from_path
from django.urls import reverse

from dal import autocomplete

from DBentry.forms import MIZAdminForm, WIDGETS
from DBentry.models import lagerort

def makeSelectionForm(model, fields, help_texts = {}, labels = {}, formfield_classes = {}):
    attrs = OrderedDict()
    for field_path in fields:
        field = get_fields_from_path(model, field_path)[-1]
        formfield_opts = dict(required = True, help_text = help_texts.get(field_path, ''))
        
        if field.is_relation:
            field = field.get_path_info()[-1].join_field
            formfield_opts['queryset'] = field.related_model._default_manager
            if field.model in WIDGETS:
                widget_dict = WIDGETS[field.model]
            else:
                widget_dict = WIDGETS
            if field.name in widget_dict:
                widget = widget_dict.get(field.name)
                # remove create_options, if possible
                #TODO: keep this? Wouldn't we want to allow people to add/change the important data?
                try:
                    reverse(widget._url+'_nocreate')
                except:
                    pass
                else:
                    widget._url = widget._url+'_nocreate'
                formfield_opts['widget'] = widget
        
        formfield_opts['label'] = labels.get(field_path, field.verbose_name.capitalize())
        if field_path in formfield_classes:
            attrs[field_path] = formfield_classes.get(field_path)(**formfield_opts)
        else:
            attrs[field_path] = field.formfield(**formfield_opts)
    return type('SelectionForm', (MIZAdminForm, ), attrs )
    
class BulkAddBestandForm(MIZAdminForm):
    
    bestand = forms.ModelChoiceField(required = True,
                                    label = "Lagerort (Bestand)", 
                                    queryset = lagerort.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'))
    dublette = forms.ModelChoiceField(required = True,
                                    label = "Lagerort (Dublette)", 
                                    queryset = lagerort.objects.all(), 
                                    widget = autocomplete.ModelSelect2(url='aclagerort'))
                                
