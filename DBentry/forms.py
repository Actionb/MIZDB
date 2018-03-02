from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import FilteredSelectMultiple

# Needed for DynamicChoiceForm
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager

from .models import *
from .constants import ATTRS_TEXTAREA
from DBentry.ac.widgets import wrap_dal_widget, MIZModelSelect2

from dal import autocomplete

Textarea = forms.Textarea

WIDGETS = {
            'audio'         :   autocomplete.ModelSelect2(url='acaudio'),
            'autor'         :   autocomplete.ModelSelect2(url='acautor'), 
            'bildmaterial'  :   autocomplete.ModelSelect2(url='acbildmaterial'), 
            'buch'          :   autocomplete.ModelSelect2(url='acbuch'), 
            'datei'         :   autocomplete.ModelSelect2(url='acdatei'), 
            'dokument'      :   autocomplete.ModelSelect2(url='acdokument'),  
            'genre'         :   autocomplete.ModelSelect2(url='acgenre'),  
            'memorabilien'  :   autocomplete.ModelSelect2(url='acmemorabilien'),
            'person'        :   autocomplete.ModelSelect2(url='acperson'),
            'schlagwort'    :   autocomplete.ModelSelect2(url='acschlagwort'),  
            'video'         :   autocomplete.ModelSelect2(url='acvideo'),
            
            # Artikel
            'ausgabe' : autocomplete.ModelSelect2(url='acausgabe', forward = ['magazin']), 
            
            # Audio
            'sender' : autocomplete.ModelSelect2(url='acsender'), 
            
            # Ausgaben
            'magazin' : autocomplete.ModelSelect2(url='acmagazin'),
            
            # Band 
            'musiker' : autocomplete.ModelSelect2(url='acmusiker'), 
            
            # Bestand
            bestand : {
                'ausgabe' : autocomplete.ModelSelect2(url = 'acausgabe'), 
                'buch' : autocomplete.ModelSelect2(url='acbuch'),  
                'lagerort' :  autocomplete.ModelSelect2(url='aclagerort'), 
                'provenienz' : autocomplete.ModelSelect2(url='acprov'), 
            }, 
            
            # Buch
            buch : {
                'verlag' : MIZModelSelect2(url='accapture', model_name='verlag', create_field='verlag_name'), 
                'verlag_orig' : autocomplete.ModelSelect2(url='acverlag'), 
                'sprache' : autocomplete.ModelSelect2(url='acsprache'), 
                'sprache_orig' : autocomplete.ModelSelect2(url='acsprache'),
                'buch_serie' : autocomplete.ModelSelect2(url='acbuchserie'),
            }, 
            
            # Genre
            genre : {
                'ober' : autocomplete.ModelSelect2(url='acgenre'),
            }, 
            
            # Magazin
            magazin : {
                'verlag' : autocomplete.ModelSelect2(url='acverlag'), 
                'genre' : autocomplete.ModelSelect2Multiple(url='acgenre'), 
                'ort' : autocomplete.ModelSelect2(url='acort'), 
                'info' : Textarea(attrs=ATTRS_TEXTAREA),
                'beschreibung' : Textarea(attrs=ATTRS_TEXTAREA),
            }, 
            
            # Musiker
            'instrument' : autocomplete.ModelSelect2(url='acinstrument'),
            'band' : autocomplete.ModelSelect2(url='acband'), 
            
            # Instrument -- register an empty dict of widgets for this model so as to not try to use 'instrument' dal widget for a simple charfield
            instrument : {}, 
            
            # Orte
            'herkunft' : autocomplete.ModelSelect2(url='acort'), 
            'ort' : autocomplete.ModelSelect2(url='acort'), 
            'kreis' : autocomplete.ModelSelect2(url='ackreis'), 
            'bland' : autocomplete.ModelSelect2(url='acbland', forward=['land'], attrs = {'data-placeholder': 'Bitte zuerst ein Land auswählen!'}), 
            'land' : autocomplete.ModelSelect2(url='acland'), 
            'veranstaltung' : autocomplete.ModelSelect2(url='acveranstaltung'), 
            'spielort' : autocomplete.ModelSelect2(url='acspielort'), 
            'sitz' : autocomplete.ModelSelect2(url='acort'),
            
            # Prov/Lagerort
            'lagerort' : autocomplete.ModelSelect2(url='aclagerort'), 
            provenienz : {
                'geber' : autocomplete.ModelSelect2(url='acgeber'), 
            }, 
            'provenienz' : autocomplete.ModelSelect2(url='acprov'), 
            
            # Schlagworte
            schlagwort : {
                'ober' : autocomplete.ModelSelect2(url='acschlagwort'),  
            }, 
            # Sonstige 
            'bemerkungen'   :   Textarea(attrs=ATTRS_TEXTAREA), 
            'beschreibung'  :   Textarea(attrs=ATTRS_TEXTAREA), 
            'info'          :   Textarea(attrs=ATTRS_TEXTAREA), 
            
            #WIP
#            'format' : autocomplete.ModelSelect2(url='acformat'), 
            'plattenfirma' : autocomplete.ModelSelect2(url='aclabel'), 
            'format_typ' : autocomplete.ModelSelect2(url='acformat_typ'), 
            'format_size' : autocomplete.ModelSelect2(url='acformat_size'), 
            'noise_red' : autocomplete.ModelSelect2(url='acnoisered'), 
            
}

class FormBase(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        # the change_form's (for add forms) initial data is being cleaned and provided by the method ModelBase.get_changeform_initial_data
        if 'initial' not in kwargs:
            kwargs['initial'] = {}
        initial = kwargs['initial'].copy()
        
        # since the ModelBase does not know what the formfields of its change_form are called, we may need to compare the
        # keys given in initial to the fields of the form in order to find a match
        fld_names = set(self.base_fields.keys())
        
        # Populate initial
        for k, v in initial.items():
            if k in fld_names:
                # This particular item in initial has a definitive match to a formfield
                fld_names.remove(k)
                continue
            
            # k might be a field_path, e.g. ausgabe__magazin
            for fld_name in fld_names:
                if fld_name == k.split('__')[-1]:
                    kwargs['initial'][fld_name] = v
                    break
                    
            # Remove all the field names that have already been matched, so we do not override the match with a  
            # partial match in name in subsequent loops
            fld_names = fld_names.difference(kwargs['initial'].keys())
            
            # Try to find a partial match in name, last resort
            for fld_name in fld_names:
                if fld_name in k:
                    kwargs['initial'][fld_name] = v 
                    break
                    
            fld_names = fld_names.difference(kwargs['initial'].keys())
        super(FormBase, self).__init__(*args, **kwargs)            
    
    def validate_unique(self):
        """
        Calls the instance's validate_unique() method and updates the form's
        validation errors if any were raised.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as e:
            # Ignore non-unique entries in the same set
            self.cleaned_data['DELETE']=True
            self._update_errors(e)

def makeForm(model, fields = [], form_class = None):
    fields_param = fields or '__all__'
    form_class = form_class or FormBase
    
    import sys
    modelname = model._meta.model_name
    thismodule = sys.modules[__name__]
    formname = '{}Form'.format(str(modelname).capitalize())
    #Check if a proper Form already exists:
    if hasattr(thismodule, formname):
        return getattr(thismodule, formname)
    from DBentry.ac.widgets import make_widget
    widget_list = {}
    for field in model.get_foreignfields():
        widget_list[field.name] = make_widget(field.related_model._meta.model_name, wrap=False, create_field=field.related_model.create_field)
#    #Otherwise use modelform_factory to create a generic Form with custom widgets
#    widget_list =  WIDGETS
#    if model in WIDGETS:
#        widget_list = WIDGETS[model]
    return forms.modelform_factory(model = model, form=form_class, fields = fields_param, widgets = widget_list) 


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
                                    widget = wrap_dal_widget(autocomplete.ModelSelect2(url='acmagazin'))) 
    class Meta:
        widgets = {'ausgabe': autocomplete.ModelSelect2(url='acausgabe', forward = ['magazin'], 
                                    attrs = {'data-placeholder': 'Bitte zuerst ein Magazin auswählen!'}),
                                    }
                                    
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
                'ausgabe' : autocomplete.ModelSelect2(url='acausgabe', forward = ['magazin'], 
                    attrs = {'data-placeholder': 'Bitte zuerst ein Magazin auswählen!'}), 
                'schlagzeile'       : Textarea(attrs={'rows':2, 'cols':90}), 
                'zusammenfassung'   : Textarea(attrs=ATTRS_TEXTAREA), 
                'info'              : Textarea(attrs=ATTRS_TEXTAREA), 
        }
        
class MIZAdminForm(forms.Form):
    """ Basic form that looks and feels like a django admin form."""
    
    def __init__(self, *args, **kwargs):
        super(MIZAdminForm, self).__init__(*args, **kwargs)
        wrapped = False
        for fld in self.fields.values():
            if isinstance(fld.widget, autocomplete.ModelSelect2):
                fld.widget = wrap_dal_widget(fld.widget)
                wrapped = True
        if wrapped and 'admin/js/admin/RelatedObjectLookups.js' not in self.Media.js:
            self.Media.js.append('admin/js/admin/RelatedObjectLookups.js')
        
    class Media:
        css = {
            'all' : ('admin/css/forms.css', )
        }
        js = ['admin/js/collapse.js']
    
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
