from django import forms
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager
from django.utils.translation import gettext_lazy
from django.utils.functional import cached_property
from DBentry.utils import snake_case_to_spaces, ensure_jquery


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
        
        
class MIZAdminFormMixin(object):
    """A mixin that adds django admin media and fieldsets."""

    class Media:
        css = {
            'all' : ('admin/css/forms.css', )
        }

    def __iter__(self):
        fieldsets = getattr(self, 'fieldsets', [(None, {'fields':list(self.fields.keys())})])

        from DBentry.helper import MIZFieldset
        for name, options in fieldsets:  
            yield MIZFieldset(
                self, name,
                **options
            )

    @property
    def media(self):
        # Collect the media needed for all the widgets
        media = super().media
        # Collect the media needed for all fieldsets; this will add collapse.js if necessary (from django.contrib.admin.options.helpers.Fieldset)
        for fieldset in self.__iter__():
            media += fieldset.media
        # Ensure jquery proper is loaded first before any other files that might reference it
        # Add the django jquery init file (it includes jquery into django's namespace)
        from django.conf import settings
        jquery_media = forms.Media(js  = [
            'admin/js/vendor/jquery/jquery%s.js' % ('' if settings.DEBUG else '.min'), 
            'admin/js/jquery.init.js' 
        ])
        return ensure_jquery(jquery_media + media)

    @cached_property
    def changed_data(self):
        data = []
        for name, field in self.fields.items():
            prefixed_name = self.add_prefix(name)
            data_value = field.widget.value_from_datadict(self.data, self.files, prefixed_name)
            if not field.show_hidden_initial:
                # Use the BoundField's initial as this is the value passed to the widget.
                initial_value = self[name].initial
                try:
                    # forms.Field does not convert the initial_value to the
                    # field's python type (like it does for the data_value)
                    # for its has_changed check.
                    # This results in IntegerField.has_changed('1',1) returning False.
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
        
class MIZAdminForm(MIZAdminFormMixin, forms.Form):
    pass

class DynamicChoiceForm(forms.Form):
    """ 
    A form that dynamically sets choices for instances of ChoiceFields from keyword arguments provided. 
    Takes a keyword argument 'choices' that can either be:
        - a dict: a mapping of a field's name to its choices
        - an iterable containing choices that apply to all ChoiceFields
    The actual choices for a given field can be lists/tuples, querysets or manager instances.
    """
    #TODO: this cannot handle grouped choices (grouped by names)

    def __init__(self, *args, **kwargs):
        all_choices = kwargs.pop('choices', {})
        super().__init__(*args, **kwargs)
        for fld_name, fld in self.fields.items():
            if isinstance(fld, forms.ChoiceField) and not fld.choices:
                if not isinstance(all_choices, dict):
                    # choice_dict is a list, there is only one choice for any ChoiceFields
                    choices = all_choices
                else:
                    choices = all_choices.get(self.add_prefix(fld_name), [])

                if isinstance(choices, BaseManager):
                    choices = choices.all()
                if isinstance(choices, QuerySet):
                    choices = [(i.pk, i.__str__()) for i in choices]

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

