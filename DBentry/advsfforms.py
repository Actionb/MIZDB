from django import forms
from django.contrib.admin.utils import get_fields_from_path
from django.utils.datastructures import MultiValueDict
from collections import OrderedDict

from .models import *
from .constants import *

from dal import autocomplete

FORWARDABLE = {
    'ausgabe' : 'magazin', 
    'bland' : 'land', 
}

class AdvSFForm(forms.Form):            
    
    def get_initial_for_field(self, field, field_name):
        """
        Return initial data for field on form. Use initial data from the form
        or the field, in that order. Evaluate callable values.
        """
        # By default, value would be set via self.initial.get - if initial is a MultiValueDict, we want to set it to the entire list though
        # This could also be fixed by:
        # - always taking field.initial before field_name: get(field.initial, field_name)
        # - moving everything out of initial into fields.initial during __init__
        # - by not providing initial to __init__ and manually assigning fields.initial after creation
        # NOTE: all kinds of forms may benefit from this, as long as they are using some form of SelectMultiple
        if isinstance(self.initial, MultiValueDict):
            value = self.initial.getlist(field_name, field.initial)
        else:
            value = self.initial.get(field_name, field.initial)
        if callable(value):
            value = value()
        return value
    
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
    
from DBentry.ac.urls import patterns_by_model
def advSF_factory(model_admin, labels = {}, formfield_classes = {}):
    """
    Handles the creation of all the autocomplete formfields.
    """
    model = model_admin.model
    attrs = OrderedDict()
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})
    for field_path in asf_dict.get('selects', []):
        rel_or_field = get_fields_from_path(model, field_path)[-1]

        if not rel_or_field.is_relation:
            # Let the template/the tag deal with the non-relation (choice) selects
            continue
        field = rel_or_field.get_path_info()[-1].join_field
        formfield_opts = dict(required = False, help_text = '', empty_label = None)
        formfield_opts['label'] = labels.get(field_path, None) or field.verbose_name.capitalize()
        formfield_opts['queryset'] = field.related_model._default_manager
        
        url = ''
        for pattern in patterns_by_model(field.related_model):
            if 'create_field' not in pattern.callback.view_initkwargs:
                url = pattern.name
                break
        if url:
            widget_opts = dict(url=url)
            if field.name in FORWARDABLE:
                forward = ''
                for other_field_path in asf_dict.get('selects', []):
                    if other_field_path.split('__')[-1] == FORWARDABLE[field.name]:
                        forward = other_field_path
                        break
                if forward:
                    widget_opts['forward'] = [forward]
                    placeholder_txt = 'Bitte zuerst ein {} auswählen!'.format(get_fields_from_path(model, forward)[-1].get_path_info()[-1].join_field.verbose_name.capitalize())
                    widget_opts['attrs'] = {'data-placeholder':placeholder_txt}
            if rel_or_field.many_to_many:
                formfield_opts['widget'] = autocomplete.ModelSelect2Multiple(**widget_opts)
            else:
                formfield_opts['widget'] = autocomplete.ModelSelect2(**widget_opts)
                
        if field_path in formfield_classes:
            attrs[field_path] = formfield_classes.get(field_path)(**formfield_opts)
        else:
            attrs[field_path] = field.formfield(**formfield_opts)
    return type('AdvSF'+model.__name__, (AdvSFForm, ), attrs )
    
