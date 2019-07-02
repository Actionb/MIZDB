
from django import forms
from django.core import exceptions
from django.db.models import lookups as django_lookups
from django.db.models.constants import LOOKUP_SEP
from django.db.models.query import QuerySet
from django.utils.datastructures import MultiValueDict
from collections import OrderedDict

from DBentry.ac.widgets import make_widget
from DBentry.forms import MIZAdminForm

from .utils import get_dbfield_from_path, strip_lookups_from_path, validate_lookups

#TODO: have 'and'/'or' checkboxes for SelectMultiple

class RangeWidget(forms.MultiWidget):
    class Media:
        css = {
            'all' : ('admin/css/rangewidget.css', )
        }
    template_name = 'rangewidget.html'
    
    def __init__(self, widget, attrs = None):
        super().__init__(widgets = [widget]*2, attrs = attrs)
        
    def decompress(self, value):
        if value:
            return value.split(',')
        return [None, None]
        
class RangeFormField(forms.MultiValueField):
    """
    A wrapper around a formfield that duplicates the field for use 
    in a __range lookup.
    """
    
    widget = RangeWidget
    
    def __init__(self, formfield, require_all_fields = False, **kwargs):
        if not kwargs.get('widget', None):
            kwargs['widget'] = RangeWidget(formfield.widget)
        self.empty_values = formfield.empty_values
        super().__init__(fields = [formfield]*2, require_all_fields = require_all_fields, **kwargs)
        
    def get_initial(self, initial, name):
        widget_data = self.widget.value_from_datadict(initial, None, name)
        if isinstance(self.fields[0], forms.MultiValueField):
            return [self.fields[0].compress(widget_data[0]), self.fields[1].compress(widget_data[1])]
        else:
            return widget_data
    
    def clean(self, value):
        return [self.fields[0].clean(value[0]), self.fields[1].clean(value[1])]
    
class SearchForm(forms.Form):
    class Media:
        css = {
            'all' : ('admin/css/forms.css', 'admin/css/search_form.css')
        }
        js = ['admin/js/remove_empty_fields.js', 'admin/js/collapse.js']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial = self.prepare_initial(self.initial)
        
    def get_initial_for_field(self, field, field_name):
        if not field_name in self.initial and isinstance(field, forms.MultiValueField):
            # Only the individual subfields show up in a request payload.
            if isinstance(field, RangeFormField):
                return field.get_initial(self.initial, field_name)
            widget_data = field.widget.value_from_datadict(self.initial, None, field_name)
            return field.compress(widget_data)
        return super().get_initial_for_field(field, field_name)        
        
    def prepare_initial(self, initial):
        # Need to map request querystring to formfields
        # Need to flatten request payload for all non-select multiple
        cleaned = {}
        if isinstance(initial, MultiValueDict):
            iterator = initial.lists()
        else:
            iterator = initial.items()
        for k, v in iterator:
            if isinstance(v, (list, tuple)) and len(v) <= 1:
                cleaned[k] = v[0] if v else None
            else:
                cleaned[k] = v
        return cleaned
        
    def get_filters_params(self):
        params = {}
        if not self.is_valid():
            return params
            
        for field_name, value in self.cleaned_data.items():
            formfield = self.fields[field_name]
            if self.lookups.get(field_name, False):
                param_key = "%s__%s" % (field_name, LOOKUP_SEP.join(self.lookups[field_name]))
            else:
                param_key = field_name
            param_value = value
            
            if isinstance(formfield, RangeFormField):
                start, end = value
                start_empty = start in formfield.empty_values
                end_empty = end in formfield.empty_values
                if start_empty and end_empty:
                # start and end are empty: just skip it.
                    continue
                elif not start_empty and end_empty:
                    # start but no end: exact lookup for start
                    param_key = field_name
                    param_value = start
                elif start_empty and not end_empty:
                    # no start but end: lte lookup for end
                    param_key = field_name + LOOKUP_SEP + self.range_upper_bound.lookup_name
                    param_value = end
            elif value in formfield.empty_values or \
                isinstance(value, QuerySet) and not value.exists():
                # Dont want empty values as filter parameters!
                continue
                
            params[param_key] = param_value 
        return params
        
class MIZAdminSearchForm(MIZAdminForm, SearchForm):
    pass
    
class SearchFormFactory:
    
    range_lookup = django_lookups.Range
    range_upper_bound = django_lookups.LessThanOrEqual
    
    def __call__(self, *args, **kwargs):
        return self.get_search_form(*args, **kwargs)
        
    def get_default_lookup(self, formfield):
        if isinstance(formfield.widget, forms.SelectMultiple):
            return ['in']
        elif isinstance(formfield, (forms.CharField, forms.Textarea)):
            return ['icontains']
        return []
        
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
        if formfield_callback is None:
            formfield_callback = self.formfield_for_dbfield
        if not callable(formfield_callback): 
            raise TypeError('formfield_callback must be a function or callable')
        
        # Create the formfields.
        fields = fields or []
        range_lookup_name = self.range_lookup.lookup_name
        attrs = OrderedDict()
        lookup_mapping = {}
        for path in fields:
            try:
                db_field, lookups = self.resolve_to_dbfield(model, path)
                validate_lookups(db_field, lookups)
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
                
            formfield_name = strip_lookups_from_path(path, lookups)
            
            formfield = formfield_callback(db_field, **formfield_kwargs)
            if range_lookup_name in lookups:
                attrs[formfield_name] = RangeFormField(formfield, required = False, **formfield_kwargs)
            else:
                attrs[formfield_name] = formfield
            
            if not lookups:
                lookups = self.get_default_lookup(formfield)
            lookup_mapping[formfield_name] = lookups
                
        base_form = form or SearchForm
        attrs['lookups'] = lookup_mapping
        attrs['range_lookup'] = self.range_lookup
        attrs['range_upper_bound'] = self.range_upper_bound
        return type('SearchForm', (base_form, ), attrs)
        
searchform_factory = SearchFormFactory()
            
        
        
        
        
        
    
