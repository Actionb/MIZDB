from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple

# Needed for DynamicChoiceForm
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager

from .models import *
from .constants import ATTRS_TEXTAREA
from DBentry.ac.widgets import make_widget
from DBentry.utils import snake_case_to_spaces, get_model_fields

Textarea = forms.Textarea           

class FormBase(forms.ModelForm):
    
#    def __init__(self, *args, **kwargs):
#        # the change_form's (for add forms) initial data is being cleaned and provided by the method ModelBase.get_changeform_initial_data
#        if 'initial' not in kwargs:
#            kwargs['initial'] = {}
#        initial = kwargs['initial'].copy()
#        
#        # since the ModelBase does not know what the formfields of its change_form are called, we may need to compare the
#        # keys given in initial to the fields of the form in order to find a match
#        fld_names = set(self.base_fields.keys())
#        
#        # Populate initial
#        for k, v in initial.items():
#            if k in fld_names:
#                # This particular item in initial has a definitive match to a formfield
#                fld_names.remove(k)
#                continue
#            
#            # k might be a field_path, e.g. ausgabe__magazin
#            for fld_name in fld_names:
#                if fld_name == k.split('__')[-1]:
#                    kwargs['initial'][fld_name] = v
#                    break
#                    
#            # Remove all the field names that have already been matched, so we do not override the match with a  
#            # partial match in name in subsequent loops
#            fld_names = fld_names.difference(kwargs['initial'].keys())
#            
#            # Try to find a partial match in name, last resort
#            for fld_name in fld_names:
#                if fld_name in k:
#                    kwargs['initial'][fld_name] = v 
#                    break
#                    
#            fld_names = fld_names.difference(kwargs['initial'].keys())
#        super(FormBase, self).__init__(*args, **kwargs)            
    
    def validate_unique(self):
        """
        Calls the instance's validate_unique() method and updates the form's
        validation errors if any were raised.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            # Ignore non-unique entries in the same formset; see django.contrib.admin.options.InlineModelAdmin.get_formset.inner
            self.cleaned_data['DELETE']=True
            self._update_errors(e) #NOTE: update errors even if we're ignoring the ValidationError?

def makeForm(model, fields = (), form_class = None):
    fields_param = fields or '__all__'
    form_class = form_class or FormBase
    
    #Check if a proper Form already exists:
    import sys
    model_name = model._meta.model_name
    thismodule = sys.modules[__name__]
    formname = model_name.capitalize() + 'Form'
    if hasattr(thismodule, formname):
        return getattr(thismodule, formname)
    
    #Otherwise use modelform_factory to create a generic Form with custom dal widgets
    widgets = {}
    for field in get_model_fields(model, base = False, foreign = True, m2m = False):
        if fields and field.name not in fields:
            continue
        widgets[field.name] = make_widget(
            model_name = field.related_model._meta.model_name, 
            create_field=field.related_model.create_field
        )
    for field in model._meta.get_fields():
        if isinstance(field, models.TextField):
            widgets[field.name] = forms.Textarea(attrs=ATTRS_TEXTAREA)
    return forms.modelform_factory(model = model, form=form_class, fields = fields_param, widgets = widgets) 


class AusgabeMagazinFieldForm(FormBase):
    """
    In order to limit search results, forward ausgabe search results to a ModelChoiceField for the model magazin.
    Useable by any ModelForm that uses a relation to ausgabe.
    Any form that inherits AusgabeMagazinFieldMixin.Meta and declares widgets in its inner Meta, must also redeclare the widget for ausgabe.
    As such, it is not very useful to inherit the Meta.    (Python inheritance rules apply)
    """
    magazin = forms.ModelChoiceField(required = False,
                                    label = "Magazin", 
                                    queryset = magazin.objects.all(), 
                                    widget = make_widget(model=magazin, wrap=True, can_delete_related=False) 
                                    )
    class Meta:
        widgets = {'ausgabe': make_widget(model_name = 'ausgabe', forward = ['magazin'])}
                                    
    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs and kwargs['instance']:
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            kwargs['initial']['magazin'] = kwargs['instance'].ausgabe.magazin
        super(AusgabeMagazinFieldForm, self).__init__(*args, **kwargs)

class InLineAusgabeForm(AusgabeMagazinFieldForm):
    # modelform_factory (called by InLineModelAdmin.get_formset) creates the Meta class attribute model, so no bad mojo for not declaring it in a Meta class
    # this ModelForm is used as for a ModelAdmin inline formset. Its Meta class will be inherited from its parent (modelform_factory:521).
    pass  

class ArtikelForm(AusgabeMagazinFieldForm):
    class Meta:
        model = artikel
        fields = '__all__'
        widgets = {
                'ausgabe': make_widget(model_name = 'ausgabe', forward = ['magazin']),               
                'schlagzeile'       : Textarea(attrs={'rows':2, 'cols':90}), 
                'zusammenfassung'   : Textarea(attrs=ATTRS_TEXTAREA), 
                'info'              : Textarea(attrs=ATTRS_TEXTAREA), 
        }
        
#TODO: make a OneRequiredForm 
        
class AutorForm(FormBase):
    
    def clean(self):
        # The user has to fill out at least kuerzel or person
        cleaned_data = super().clean()
        if cleaned_data.get('kuerzel') or cleaned_data.get('person'):
            return cleaned_data
        else:
            raise ValidationError('Bitte mindestens eines dieser Felder ausfüllen: Kürzel, Person')
            
class BuchForm(FormBase):
    class Meta:
        widgets = {
            'titel' : Textarea(attrs={'rows':1, 'cols':90}), 
            'titel_orig': Textarea(attrs={'rows':1, 'cols':90}), 
            'buchband' : make_widget(url='acbuchband', model=buch, wrap=False, can_delete_related=False),
        }
    
    def clean(self):
        # The user must not fill out both is_buchband and buchband
        cleaned_data = super().clean()
        if cleaned_data.get('is_buchband') and cleaned_data.get('buchband'):
            raise ValidationError('Ein Buchband kann nicht selber Teil eines Buchbandes sein.')
        else:
            return cleaned_data
        
class HerausgeberForm(FormBase):
    
    def clean(self):
        # The user has to fill out at least person or organisation
        cleaned_data = super().clean()
        if cleaned_data.get('person') or cleaned_data.get('organisation'):
            return cleaned_data
        else:
            raise ValidationError('Bitte mindestens eines dieser Felder ausfüllen: Person, Organisation')
        
class MIZAdminForm(forms.Form):
    """ Basic form that looks and feels like a django admin form."""
        
    class Media:
        #TODO: have a look at contrib.admin.options.ModelAdmin.media
        css = {
            'all' : ('admin/css/forms.css', )
        }
        js = ['admin/js/collapse.js', 'admin/js/admin/RelatedObjectLookups.js']
    
    def __iter__(self):
        fieldsets = getattr(self, 'fieldsets', [(None, {'fields':list(self.fields.keys())})])
            
        from .helper import MIZFieldset
        for name, options in fieldsets:  
            yield MIZFieldset(
                self, name,
                **options
            )
        
    @property
    def media(self):
        media = super(MIZAdminForm, self).media
        for fieldset in self.__iter__():
            # Add collapse.js if necessary
            media += fieldset.media         # Fieldset Media, since forms.Form checks self.fields instead of self.__iter__
        # Ensure jquery is loaded first
        extra = '' if settings.DEBUG else '.min'
        media._js.insert(0, 'admin/js/jquery.init.js')
        media._js.insert(0, 'admin/js/vendor/jquery/jquery%s.js' % extra)
        return media
        
    @cached_property
    def changed_data(self):
        data = []
        for name, field in self.fields.items():
            prefixed_name = self.add_prefix(name)
            data_value = field.widget.value_from_datadict(self.data, self.files, prefixed_name)
            if not field.show_hidden_initial:
                # Use the BoundField's initial as this is the value passed to
                # the widget.
                initial_value = self[name].initial
                try:
                    # Convert the initial_value to the field's type
                    # If field is an IntegerField and has initial of type str, field.has_changed will return false
                    initial_value = field.to_python(initial_value)
                except:
                    pass
            else:
                initial_prefixed_name = self.add_initial_prefix(name)
                hidden_widget = field.hidden_widget()
                try:
                    initial_value = field.to_python(hidden_widget.value_from_datadict(
                        self.data, self.files, initial_prefixed_name))
                except ValidationError:
                    # Always assume data has changed if validation fails.
                    data.append(name)
                    continue
            if field.has_changed(initial_value, data_value):
                data.append(name)
        return data
                    
class DynamicChoiceForm(forms.Form):
    """ A form that dynamically sets choices for ChoiceFields from keyword arguments provided. 
        Accepts lists and querysets (as well as Manager instances).
        If a ChoiceField's name is not represented in kwargs, the form will try to set that field's choices to a 'qs' or 'queryset' keyword argument.
    """
    
    def __init__(self, *args, **kwargs):
        choice_dict = kwargs.pop('choices', {})
        super(DynamicChoiceForm, self).__init__(*args, **kwargs)
        for fld_name, fld in self.fields.items():
            if isinstance(fld, forms.ChoiceField) and not fld.choices:
                if not isinstance(choice_dict, dict):
                    # choice_dict is a list, there is only one choice for any ChoiceFields
                    choices = choice_dict
                else:
                    choices = choice_dict.get(self.add_prefix(fld_name), [])
                    
                if isinstance(choices, BaseManager):
                    choices = choices.all()
                if isinstance(choices, QuerySet):
                    choices = [(i.pk, i.__str__()) for i in choices]
                    
                #NOTE: these can never be true after the first if else
                if isinstance(choices, dict): 
                    choices = [(k, v) for k, v in choices.items()]
                if not isinstance(choices, (list, tuple)):
                    choices = list(choices)
                
                new_choices = []
                for i in choices:
                    try:
                        k = str(i[0])
                        v = str(i[1])
                    except IndexError:
                        # i is an iterable with len < 2)
                        k = v = str(i[0])
                    except TypeError:
                        # i is not an iterable
                        k = v = str(i)
                    new_choices.append( (k, v) )
                choices = new_choices
                fld.choices = choices
                
class DynamicChoiceFormSet(forms.formsets.BaseFormSet):
    #NOTE: probably not needed anymore
    
    def get_form_kwargs(self, index):
        if index is None:
            return super(DynamicChoiceFormSet, self).get_form_kwargs(index)
        form_kwargs = {}
        for fld_name, fld in self.form.base_fields.items():
            # DynamicChoiceForm expects kwargs in the format prefix+fld_name to set that field's choices to
            kwarg_name = self.add_prefix(index) + '-' + fld_name
            if kwarg_name in self.form_kwargs:
                form_kwargs[kwarg_name] = self.form_kwargs.get(kwarg_name) #NOTE .copy()?
        return form_kwargs
        

class FavoritenForm(MIZAdminForm, forms.ModelForm):
    class Meta:
        model = Favoriten
        fields = '__all__'
        widgets = {
            'fav_genres'    :   FilteredSelectMultiple('Genres', False), 
            'fav_schl'      :   FilteredSelectMultiple('Schlagworte', False),
        }
        
class XRequiredFormMixin(object):
    """
    A mixin that allows setting a minimum/maximum number of groups of fields to be required.
    
    Attributes:
    - xrequired: an iterable of dicts that specicify the number of required fields ('min', 'max'), the field names
                ('fields') and optionally a custom error message ('error_message'). 
    - default_error_messages: a dict of default error messages for min and max ValidationErrors
    """
    
    xrequired = None 
    default_error_messages = {
        'min' : gettext_lazy('Bitte mindestens {min} dieser Felder ausfüllen: {fields}.'), 
        'max' : gettext_lazy('Bitte höchstens {max} dieser Felder ausfüllen: {fields}.'), 
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.xrequired:
            for required in self.xrequired:
                for field_name in required['fields']:
                    self.fields[field_name].required = False

    def clean(self):
        if self.xrequired:
            for required in self.xrequired:
                min = required.get('min', 0)
                max = required.get('max', 0)
                if not min and not max:
                    continue
                    
                fields_with_values = 0
                for field_name in required['fields']:
                    if self.cleaned_data.get(field_name):
                        fields_with_values += 1
                        
                min_error = max_error = False
                if min and fields_with_values < min:
                    min_error = True
                if max and fields_with_values > max:
                    max_error = True
                    
                custom_error_msgs = required.get('error_message', {})
                fields = ", ".join(
                    self.fields[field_name].label if self.fields[field_name].label else snake_case_to_spaces(field_name).title()
                    for field_name in required['fields']
                )
                if min_error:
                    msg = custom_error_msgs.get('min') or self.default_error_messages['min']
                    msg = msg.format(min = min, fields = fields)
                    self.add_error(None, msg)
                if max_error:
                    msg = custom_error_msgs.get('max') or self.default_error_messages['max']
                    msg = msg.format(max = max, fields = fields)
                    self.add_error(None, msg)
        return super().clean()
    
    
