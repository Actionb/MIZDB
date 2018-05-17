from django import forms
from django.contrib.admin.utils import get_fields_from_path
from django.utils.datastructures import MultiValueDict
from collections import OrderedDict

from .models import *
from .constants import *
from DBentry.ac.widgets import make_widget

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
        if field_name.endswith('magazin') and 'ausgabe' in self.initial:
            return ausgabe.objects.get(pk=self.initial.get('ausgabe')).magazin
        
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
            
    class Media:
        js = ['admin/js/collapse.js', 'admin/js/advanced_search_form.js']
    
def advSF_factory(model_admin, labels = {}, formfield_classes = {}):
    """
    Handles the creation of all the autocomplete formfields.
    """
    model = model_admin.model
    attrs = OrderedDict()
    
    asf_dict = getattr(model_admin, 'advanced_search_form', {})
    for field_path in asf_dict.get('selects', []):
        if isinstance(field_path, (list, tuple)):
            field_path, forward = field_path
        else:
            forward = []
        rel_or_field = get_fields_from_path(model, field_path)[-1]

        if not rel_or_field.is_relation:
            # Let the template/the tag deal with the non-relation (choice) selects
            continue
        
        if rel_or_field.one_to_many:
            # This is a ManyToOneRel defining a 'reverse' relation:
            field = rel_or_field.remote_field # the ForeignKey field
            # The ForeignKey's related_model points back to *this* model, we need the relation's related_model
            related_model = rel_or_field.related_model 
            label = related_model._meta.verbose_name.capitalize()
        else:
            field = rel_or_field.get_path_info()[-1].join_field
            related_model = field.related_model
            label = field.verbose_name.capitalize()
            
        formfield_opts = dict(required = False, help_text = '', empty_label = None)
        formfield_opts['label'] = labels.get(field_path, None) or label
        formfield_opts['queryset'] = related_model.objects
        
        # Create an autocomplete widget
        widget_opts = dict(url='accapture', model=related_model, multiple=rel_or_field.many_to_many, can_add_related=False)
        if forward:
            widget_opts['forward'] = forward
        formfield_opts['widget'] = make_widget(**widget_opts)
                        
        if field_path in formfield_classes:
            attrs[field_path] = formfield_classes.get(field_path)(**formfield_opts)
        else:
            attrs[field_path] = field.formfield(**formfield_opts)
    return type('AdvSF'+model.__name__, (AdvSFForm, ), attrs )
