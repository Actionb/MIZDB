from django import forms
from django.contrib.admin.helpers import Fieldset
from django.core.exceptions import ValidationError
from django.db.models.query import QuerySet
from django.db.models.manager import BaseManager
from django.utils.translation import gettext_lazy
from django.utils.functional import cached_property

from dbentry.constants import discogs_release_id_pattern
from dbentry.utils import snake_case_to_spaces
from dbentry.validators import DiscogsURLValidator


class FieldGroup:
    """
    Helper object managing a group of fields for the MinMaxRequiredFormMixin.

    Created during the clean() method of a form instance, a FieldGroup can
    assess whether or not its minimum/maximum requirements are fulfilled.
    """

    def __init__(self, form, *, fields, min_fields=None, max_fields=None,
                 error_messages=None, format_callback=None, **_kwargs
                 ):
        """
        Constructor for the FieldGroup.

        Parameters:
            form: the form instance this FieldGroup belongs to.
            fields (list): this group's field names.
            min_fields (int): the minimum number of fields that need to be filled out.
            max_fields (int): the maximum number of fields that may be filled out.
            error_messages (dict): a mapping of error_type (i.e. 'min','max')
                to (ValidationError) error message.
            format_callback (callable or str): a callable or the name of a
                method of this group's form used to format the error messages.
        """

        self.form = form
        self.fields = fields
        self.min, self.max = min_fields, max_fields
        self.error_messages = self.form.get_group_error_messages(
            group=self, error_messages=error_messages or {},
            format_callback=format_callback
        )

    def fields_with_values(self):
        """
        Count the number of formfields that have a non-empty value.

        Returns:
            int: the number of formfields that have a non-empty value.
        """
        result = 0
        for field in self.fields:
            if field not in self.form.fields:
                continue
            formfield = self.form.fields[field]
            value = self.form.cleaned_data.get(field, None)
            if ((isinstance(formfield, forms.BooleanField) and not value)
                    or value in formfield.empty_values):
                continue
            result += 1
        return result

    def has_min_error(self, fields_with_values):
        return self.min and fields_with_values < self.min

    def has_max_error(self, fields_with_values):
        return self.max and fields_with_values > self.max

    def check(self):
        if not self.min and not self.max:
            return False, False
        fields_with_values = self.fields_with_values()
        min_error = self.has_min_error(fields_with_values)
        max_error = self.has_max_error(fields_with_values)
        return min_error, max_error


# noinspection PyUnresolvedReferences
class MinMaxRequiredFormMixin(object):
    """
    A mixin that allows setting groups of fields to be required.

    By default, error messages are formatted with the number
    of fields minimally (format kwarg: 'min') or maximally ('max') required and
    a comma separated list of those fields ('fields').

    Attributes:
        minmax_required: an iterable of dicts, essentially the keyword
            arguments for the FieldGroups.
            See 'FieldGroup' constructor args for more details.
        min_error_message (str): the default error message for a min error.
        max_error_message (str): the default error message for a max error.

    Examples:
        class MyForm(MinMaxRequiredFormMixin, forms.Form):
            spam = forms.IntegerField()
            bacon = forms.IntegerField()
            egg = forms.IntegerField()

            max_error_message = "Too much spam!"
            minmax_required = [{
                'min': 1, 'max': 2, 'fields': ['spam', 'bacon', 'egg'],
                'error_messages' = {
                    'min': 'Must have at least {min!s} of {fields}, {remark}!',
                },
                'format_callback': 'spam_callback'
            }]

            def spam_callback(self, group, error_messages, format_kwargs):
                remark = "good Sir!"
                if self.user.is_viking:
                    remark = "you vile Viking!"
                return {
                    error_type: msg.format(remark=remark, **format_kwargs)
                    for error_type, msg in error_messages.items()
                }

        If none of the three fields has data and the user is a viking
        the form will display the min error:
            "Must have at least 1 of Spam, Bacon, Egg, you vile Viking!"
        If all three fields have data, the default max error will be shown
        (as minmax_required does not define a custom error for that group):
            "Too much spam!"
    """

    minmax_required = None
    min_error_message = gettext_lazy(
        'Bitte mindestens {min!s} dieser Felder ausfüllen: {fields}.'
    )
    max_error_message = gettext_lazy(
        'Bitte höchstens {max!s} dieser Felder ausfüllen: {fields}.'
    )

    def __init__(self, *args, **kwargs):
        self.default_error_messages = {
            'min': self.min_error_message,
            'max': self.max_error_message
        }

        super().__init__(*args, **kwargs)

        self._groups = []
        # Check that field names specified in the group_kwargs are present
        # on the form and set the 'required' attribute of those formfields
        # to False.
        for group_kwargs in self.minmax_required or []:
            fields = group_kwargs.get('fields', [])
            if not fields:
                continue
            try:
                for field in fields:
                    self.fields[field].required = False
            except KeyError:
                # At least one field in that group does not have a
                # corresponding formfield; skip the entire group.
                continue
            self._groups.append(group_kwargs)

    def get_groups(self):
        """Instantiate the helper objects."""
        for group_kwargs in self._groups:
            yield FieldGroup(self, **group_kwargs)

    def clean(self):
        for group in self.get_groups():
            min_error, max_error = group.check()
            if min_error:
                self.add_group_error('min', group)
            if max_error:
                self.add_group_error('max', group)
        return super().clean()

    def add_group_error(self, error_type, group):
        self.add_error(None, group.error_messages[error_type])

    def get_error_message_format_kwargs(self, group):
        return {
            'fields': self._get_message_field_names(group),
            'min': group.min or '0',
            'max': group.max or '0',
        }

    def _get_message_field_names(self, group):
        return ", ".join(
            self.fields[field_name].label or
            snake_case_to_spaces(field_name).title()
            for field_name in group.fields
            if field_name in self.fields
        )

    def get_group_error_messages(self, group, error_messages, format_callback=None):
        """
        Prepare and format the error messages for the given group.

        If a format_callback is provided (which can be either a callable or
        the name of a method of this form instance), it will be called with
        the following args:
            self: this form's instance
            group (FieldGroup): the given group
            error_messages (dict): custom error messages to be formatted
                directly passed through from declarations in 'minmax_required'
            format_kwargs (dict): some default formatting keyword arguments

        Returns:
            dict: mapping of error_type to error_message in which
                custom error messages override the default ones.
        """
        format_kwargs = self.get_error_message_format_kwargs(group)

        callback = format_callback
        if isinstance(callback, str) and hasattr(self, callback):
            # The callback is the name of a method of this form.
            # Get the function instead, so we can keep the
            # callback args consistent.
            callback = getattr(self.__class__, callback)
        if callable(callback):
            error_messages = callback(self, group, error_messages, format_kwargs)
        else:
            error_messages = {
                k: v.format(**format_kwargs)
                for k, v in error_messages.items()
            }
        defaults = self.get_default_error_messages(format_kwargs)
        return {**defaults, **error_messages}

    def get_default_error_messages(self, format_kwargs):
        messages = {}
        for error_type in ('min', 'max'):
            message = self.default_error_messages[error_type].format(
                **format_kwargs)
            messages[error_type] = message
        return messages


# noinspection PyUnresolvedReferences
class MIZAdminFormMixin(object):
    """A mixin that adds django admin media and fieldsets."""

    class Media:
        css = {
            'all': ('admin/css/forms.css',)
        }

    def __iter__(self):
        fieldsets = getattr(
            self, 'fieldsets',
            [(None, {'fields': list(self.fields.keys())})]
        )
        for name, options in fieldsets:
            yield Fieldset(self, name, **options)

    @property
    def media(self):
        # Collect the media needed for all the widgets.
        media = super().media
        # Collect the media needed for all fieldsets.
        # This will add collapse.js if necessary
        # (from django.contrib.admin.options.helpers.Fieldset).
        for fieldset in self.__iter__():
            media += fieldset.media
        return media

    @cached_property
    def changed_data(self):
        data = []
        for name, field in self.fields.items():
            prefixed_name = self.add_prefix(name)
            data_value = field.widget.value_from_datadict(
                self.data, self.files, prefixed_name
            )
            if not field.show_hidden_initial:
                # Use the BoundField's initial as this is the value passed
                # to the widget.
                initial_value = self[name].initial
                try:
                    # forms.Field does not convert the initial_value to the
                    # field's python type (like it does for the data_value)
                    # for its has_changed check.
                    # This results in IntegerField.has_changed('1',1);
                    # returning False.
                    initial_value = field.to_python(initial_value)
                except ValidationError:
                    # Always assume data has changed if validation fails.
                    data.append(name)
                    continue
            else:
                initial_prefixed_name = self.add_initial_prefix(name)
                hidden_widget = field.hidden_widget()
                try:
                    initial_value = field.to_python(
                        hidden_widget.value_from_datadict(
                            self.data, self.files, initial_prefixed_name
                        )
                    )
                except ValidationError:
                    # Always assume data has changed if validation fails.
                    data.append(name)
                    continue
            if field.has_changed(initial_value, data_value):
                data.append(name)
        return data


class MIZAdminForm(MIZAdminFormMixin, forms.Form):
    pass


# noinspection PyUnresolvedReferences
class DynamicChoiceFormMixin(object):
    """Set formfield choices after init from keyword arguments."""

    def __init__(self, choices=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if choices:
            self.set_choices(choices)

    def set_choices(self, choices):
        """
        Set choices for choice fields that do not already have choices.

        Arguments:
            choices (dict): a mapping of choicefield names to its choices.
                django.forms.models.ALL_FIELDS constant can be used to set the
                same choices to all fields that are not mentioned in 'choices'.

        django guidelines for choices apply.
        A choice can also be a manager or queryset instance.
        """
        if not isinstance(choices, dict):
            raise TypeError(
                "Expected mapping formfield_name: choices. Got %s."
                % type(choices)
            )
        for fld_name, fld in self.fields.items():
            if not isinstance(fld, forms.ChoiceField) or fld.choices:
                # Not a choice field or the choices are already set.
                continue
            if self.add_prefix(fld_name) in choices:
                field_choices = choices[self.add_prefix(fld_name)]
            elif forms.ALL_FIELDS in choices:
                field_choices = choices[forms.ALL_FIELDS]
            else:
                continue

            if isinstance(field_choices, BaseManager):
                # model.objects; need to call all() on it.
                field_choices = field_choices.all()
            if isinstance(field_choices, QuerySet):
                # We need 2-tuples (actual value, human readable name):
                fld.choices = [(str(obj.pk), str(obj)) for obj in field_choices]
            else:
                fld.choices = list(field_choices)


class MIZAdminInlineFormBase(forms.ModelForm):
    """
    A model form class that flags forms for deletion when the form's model
    instance would violate uniqueness.

    Intended to be used as base form class for inline formsets such as
    model admin inlines.
    """

    def validate_unique(self):
        """
        Call the instance's validate_unique() method and, if unique validity is
        violated, plan the deletion of this inline formset form.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            # Ignore non-unique entries in the same formset.
            self.cleaned_data['DELETE'] = True


# noinspection PyUnresolvedReferences
class DiscogsFormMixin(object):
    """
    A mixin for fields handling data from discogs.

    The form should include two fields:
        - a field that stores the release ID of a record on discogs
        - a field that stores the URL to the page of that record
    This mixin knows these fields through the attributes 'release_id_field_name'
    and 'url_field_name', and adds validation to both.
    """

    url_field_name = release_id_field_name = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.url_field_name in self.fields:
            self.fields[self.url_field_name].validators.append(
                DiscogsURLValidator())

    def clean(self):
        """Validate and clean release_id and discogs_url."""
        if (self.url_field_name in self._errors
                or self.release_id_field_name in self._errors):
            return self.cleaned_data
        release_id = str(
            self.cleaned_data.get(self.release_id_field_name, '') or '')
        discogs_url = self.cleaned_data.get(self.url_field_name) or ''
        if not (release_id or discogs_url):
            return self.cleaned_data

        match = discogs_release_id_pattern.search(discogs_url)
        if match and len(match.groups()) == 1:
            # We have a valid url with a release_id in it.
            release_id_from_url = match.groups()[-1]
            if release_id and release_id_from_url != release_id:
                raise ValidationError(
                    "Die angegebene Release ID (%s) stimmt nicht mit der ID im "
                    "Discogs Link überein (%s)." % (release_id, release_id_from_url)
                )
            elif not release_id:
                # Set release_id from the url.
                release_id = str(match.groups()[-1])
                self.cleaned_data['release_id'] = release_id
        discogs_url = "http://www.discogs.com/release/" + release_id
        self.cleaned_data['discogs_url'] = discogs_url
        return self.cleaned_data
