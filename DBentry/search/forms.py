
from django import forms
from django.contrib import admin
from django.core import exceptions
from django.db.models import lookups as django_lookups
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import QuerySet
from django.utils.datastructures import MultiValueDict
from collections import OrderedDict

from DBentry.ac.widgets import make_widget
from DBentry.forms import MIZAdminForm

from .utils import get_dbfield_from_path

class RangeWidget(forms.MultiWidget):
    
    #TODO: needs a custom template to squeeze the '-' in between the two other widgets
    
    def __init__(self, widget, attrs = None):
        super().__init__(widgets = [widget]*2, attrs = attrs)
        
    def value_from_datadict(self, data, files, name):
        # Allow an immediate lookup of 'name' instead of
        # MultiWidget's usual 'name_index'.
        if name in data:
            return data[name]
        return super().value_from_datadict(data, files, name)
        
    def decompress(self, value):
        return value.split(',')
        
class RangeFormField(forms.MultiValueField):
    """
    A wrapper around a formfield that duplicates the field for use 
    in a __range lookup.
    """
    
    widget = RangeWidget
    
    def __init__(self, formfield, require_all_fields = False, **kwargs):
        kwargs['widget'] = RangeWidget(formfield.widget)
        #NOTE: it shouldn't be necessary to set required = False, the factory already does that?
#        kwargs['required'] = False
        self.empty_values = formfield.empty_values
        super().__init__(fields = [formfield]*2, require_all_fields = require_all_fields, **kwargs)
    
    def clean(self, value):
        return [self.fields[0].clean(value[0]), self.fields[1].clean(value[1])]
    
class SearchForm(forms.Form):
    class Media:
        css = {
            'all' : ('admin/css/forms.css', )
        }
        js = ['admin/js/remove_empty_fields.js', 'admin/js/collapse.js']
        
    def get_filter_params(self):
        params = {}
        if not self.is_valid():
            return params
        range_lookup_name = self.range_lookup.lookup_name
        upper_bound_lookup_name = self.range_upper_bound.lookup_name
        for field_name, value in self.cleaned_data.items():
            formfield = self.fields[field_name]
            if isinstance(formfield, RangeFormField):
                start, end = value
                start_empty = start in formfield.empty_values
                end_empty = end in formfield.empty_values
                if not start_empty and not end_empty:
                    # start and end are not empty; we can use the range lookup
                    params[field_name] = value
                elif not start_empty and end_empty:
                    # start but no end: exact lookup for start
                    param_key = field_name.replace(LOOKUP_SEP + range_lookup_name, '')
                    params[param_key] = start
                elif start_empty and not end_empty:
                    # no start but end: lte lookup for end
                    param_key = field_name.replace(range_lookup_name, upper_bound_lookup_name)
                    params[param_key] = end
                # start and end are empty: just skip it.
            elif value in formfield.empty_values or \
                isinstance(value, QuerySet) and not value:
                # Dont want empty values as filter parameters!
                continue
            else:
                params[field_name] = value
        return params
    
    def get_initial_for_field(self, field, field_name):
        # Use getlist() if initial is a MultiValueDict and we're working on a SelectMultiple.
        if isinstance(field.widget, forms.SelectMultiple) and isinstance(self.initial, MultiValueDict):
            return self.initial.getlist(field_name, field.initial)
        return super().get_initial_for_field(field, field_name)
        
class MIZAdminSearchForm(MIZAdminForm, SearchForm):
    pass
    
class LookupRegistry:
    range_lookup= django_lookups.Range
    range_upper_bound = django_lookups.LessThanOrEqual
    
class SearchFormFactory(LookupRegistry):
    
    def __call__(self, *args, **kwargs):
        return self.get_search_form(*args, **kwargs)
        
    def resolve_to_dbfield(self, model, field_path):
        return get_dbfield_from_path(model, field_path)
        
    def formfield_for_dbfield(self, db_field, **kwargs):
        widget = kwargs.get('widget', None)
        if db_field.is_relation and widget is None: 
            # Create a dal autocomplete widget
            widget_opts = {
                'model': db_field.related_model, 'multiple': db_field.many_to_many, 
                'wrap': False, 'can_add_related': False, 
            }
            if kwargs.get('forward', None) is not None:
                widget_opts['forward'] = kwargs.pop('forward')
            kwargs['widget'] = make_widget(**widget_opts)
            # TODO: aren't these set by the respective db_field?
#            kwargs['queryset'] = db_field.related_model.objects
#            if kwargs.get('label', None) is None:
#                kwargs['label'] = db_field.verbose_name.title()
        # It's a search form, nothing is required!
        kwargs['required'] = False
        return db_field.formfield(**kwargs)
    
    def get_search_form(self, model, fields = None, form = None, formfield_callback = None, 
        widgets = None, localized_fields = None, labels = None, help_texts = None, 
        error_messages = None, field_classes = None, forwards = None):
#def fields_for_model(model, fields=None, exclude=None, widgets=None,
#                     formfield_callback=None, localized_fields=None,
#                     labels=None, help_texts=None, error_messages=None,
#                     field_classes=None, *, apply_limit_choices_to=True):
        #TODO: add 'bases' kwarg to allow overriding LookupRegistry
        if formfield_callback is None:
            formfield_callback = self.formfield_for_dbfield
        if not callable(formfield_callback): 
            raise TypeError('formfield_callback must be a function or callable')
        
        # Create the formfields.
        fields = fields or []
        range_lookup_name = self.range_lookup.lookup_name
        formfields = OrderedDict()
        for path in fields:
            try:
                db_field, lookups = self.resolve_to_dbfield(model, path)
            except (exceptions.FieldDoesNotExist, exceptions.FieldError):
                continue
                
            formfield_kwargs = {}
            if widgets and path in widgets:
                formfield_kwargs['widget'] = widgets[path]
            if localized_fields == forms.models.ALL_FIELDS \
                or (localized_fields and path in localized_fields):
                formfield_kwargs['localize'] = True
            if labels and path in labels:
                formfield_kwargs['label'] = labels[path]
            if help_texts and path in help_texts:
                formfield_kwargs['help_text'] = help_texts[path]
            if error_messages and path in error_messages:
                formfield_kwargs['error_messages'] = error_messages[path]
            if field_classes and path in field_classes:
                formfield_kwargs['form_class'] = field_classes[path]
            if forwards and path in forwards:
                formfield_kwargs['forward'] = forwards[path]
            
            formfield = formfield_callback(db_field, **formfield_kwargs)
            if range_lookup_name in lookups:
                formfields[path] = RangeFormField(formfield)
            else:
                formfields[path] = formfield
                
        base_form = form or SearchForm
        return type('SearchForm', (base_form, LookupRegistry), formfields)
        
searchform_factory = SearchFormFactory()
            
        
        
        
        
        
    
