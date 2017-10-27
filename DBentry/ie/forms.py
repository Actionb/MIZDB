#
from django import forms

from DBentry.forms import MIZAdminForm
from DBentry.models import *

class ImportSelectForm(MIZAdminForm):
    import_file = forms.FileField(allow_empty_file=False)
    check_bom = forms.BooleanField(required = False)

from django.utils.functional import cached_property
from django.forms.formsets import BaseFormSet, ManagementForm

# special field names
TOTAL_FORM_COUNT = 'TOTAL_FORMS'
INITIAL_FORM_COUNT = 'INITIAL_FORMS'
MIN_NUM_FORM_COUNT = 'MIN_NUM_FORMS'
MAX_NUM_FORM_COUNT = 'MAX_NUM_FORMS'
ORDERING_FIELD_NAME = 'ORDER'
DELETION_FIELD_NAME = 'DELETE'

# default minimum number of forms in a formset
DEFAULT_MIN_NUM = 0

# default maximum number of forms in a formset, to prevent memory exhaustion
DEFAULT_MAX_NUM = 1000
class BoundFormSet(BaseFormSet):
    """ Binds forms in the formset to their initial data. """
    
    def __init__(self, *args, **kwargs):
        super(BoundFormSet, self).__init__(*args, **kwargs)
        self.is_bound = self.data is not None or self.files is not None or self.initial is not None
        
    def initial_form_count(self):
        """Returns the number of forms that are required in this FormSet."""
        return len(self.initial) if self.initial else 0
        
    def total_form_count(self):
        return self.initial_form_count()

    @cached_property
    def management_form(self):
        """Returns the ManagementForm instance for this FormSet."""
        if self.prefix:
            prefix = self.prefix + '-'
        else:
            prefix = ''
        
        form = ManagementForm(auto_id=self.auto_id, prefix=self.prefix, data={
            prefix + TOTAL_FORM_COUNT: self.total_form_count(),
            prefix + INITIAL_FORM_COUNT: self.initial_form_count(),
            prefix + MIN_NUM_FORM_COUNT: self.min_num,
            prefix + MAX_NUM_FORM_COUNT: self.max_num})
        return form
        
    def _construct_form(self, i, **kwargs):
        """
        Instantiates and returns the i-th form instance in a formset.
        """
        defaults = {
            'auto_id': self.auto_id,
            'prefix': self.add_prefix(i),
            'error_class': self.error_class,
            # Don't render the HTML 'required' attribute as it may cause
            # incorrect validation for extra, optional, and deleted
            # forms in the formset.
            'use_required_attribute': False,
        }
        if self.is_bound:
            try:
                initial_data = self.initial[i]
            except IndexError:
                initial_data = None
            defaults['data'] = self.data or {defaults['prefix']+'-'+k:v for k, v in initial_data.items()}
            defaults['files'] = self.files
        if self.initial and 'initial' not in kwargs:
            try:
                defaults['initial'] = self.initial[i]
            except IndexError:
                pass
        # Allow extra forms to be empty, unless they're part of
        # the minimum forms.
        if i >= self.initial_form_count() and i >= self.min_num:
            defaults['empty_permitted'] = True
        defaults.update(kwargs)
        form = self.form(**defaults)
        self.add_fields(form, i)
        return form

class MBForm(MIZAdminForm):
    #zeile = forms.CharField(required=False, widget=forms.TextInput(attrs={'readonly':'readonly'}))
    name = forms.CharField()
    release_ids = forms.CharField(required=False, widget=forms.HiddenInput())
    
    
    is_musiker = forms.BooleanField(label = 'Ist Musiker', required=False)
    is_band = forms.BooleanField(label = 'Ist Band', required=False)
    is_person = forms.BooleanField(label = 'Ist Person', required=False)
    #delete = forms.BooleanField(label = 'Löschen', required=False)
    
#    def __init__(self, *args, **kwargs):
#        super(MBForm, self).__init__(data=kwargs.get('data', None) or kwargs.get('initial', None))
    
    def clean(self):
        is_band = self.cleaned_data.get('is_band', False)
        is_musiker = self.cleaned_data.get('is_musiker', False)
        is_person = self.cleaned_data.get('is_person', False)
        
        if is_band and is_person:
            raise ValidationError('Eine Band kann nicht auch eine Person sein.')
            
        if is_band and is_musiker:
            raise ValidationError('Eine Band kann nicht auch ein Musiker sein.')
            
        if not is_band and not is_musiker and not is_person:
            raise ValidationError('Bitte diesen Namen zuweisen.')
        
#        if len([i for i in [is_band, is_musiker, is_person] if i]) != 1:
#            # More than one checkbox or no checkbox was ticked
#            raise ValidationError('Bee')
    
MBFormSet = forms.formset_factory(MBForm, extra=0, can_delete=True)
