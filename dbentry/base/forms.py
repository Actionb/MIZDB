import re
import sys

if sys.version_info > (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar, Union

from django import forms
from django.core.exceptions import ValidationError
from django.db.models.manager import BaseManager
from django.db.models.query import QuerySet
from django.utils.translation import gettext_lazy

from dbentry.utils.text import snake_case_to_spaces
from dbentry.validators import DiscogsURLValidator

# Default attrs for the TextArea form widget
ATTRS_TEXTAREA = {"rows": 3, "cols": 90}

if TYPE_CHECKING:  # pragma: no cover
    # For static type checking purposes, have the mixins extend the concrete
    # base class that they are designed to be used with.
    FormMixinBase: TypeAlias = forms.Form
    ModelFormMixinBase: TypeAlias = forms.ModelForm
else:
    FormMixinBase = object
    ModelFormMixinBase = object

MinMaxForm = TypeVar("MinMaxForm", bound=Union["MinMaxRequiredFormMixin", forms.Form])


class FieldGroup:
    """
    Helper object managing a group of fields for the MinMaxRequiredFormMixin.

    Created during the clean() method of a form instance, a FieldGroup can
    assess whether its minimum/maximum requirements are fulfilled.
    """

    def __init__(
        self,
        form: MinMaxForm,
        *,
        fields: List[str],
        min_fields: Optional[int] = None,
        max_fields: Optional[int] = None,
        error_messages: Optional[Dict[str, str]] = None,
        format_callback: Optional[Union[Callable, str]] = None,
    ) -> None:
        """
        Constructor for the FieldGroup.


        Args:
            form: the form instance this FieldGroup belongs to
            fields (list): this group's field names
            min_fields (int): the minimum number of fields that need to be
                filled out
            max_fields (int): the maximum number of fields that may be
                filled out
            error_messages (dict): a mapping of error_type (i.e. 'min','max')
                to (ValidationError) error message specific to this group
            format_callback (callable or str): a callable or the name of a
                method of this group's form used to format the error messages
        """
        self.form = form
        self.fields = fields
        self.min, self.max = min_fields, max_fields
        self.error_messages = self.form.get_group_error_messages(
            group=self, error_messages=error_messages or {}, format_callback=format_callback
        )

    def fields_with_values(self) -> int:
        """Count the number of formfields that have a non-empty value."""
        result = 0
        for field in self.fields:
            if field not in self.form.fields:
                continue
            formfield = self.form.fields[field]
            value = self.form.cleaned_data.get(field, None)
            if (isinstance(formfield, forms.BooleanField) and not value) or value in formfield.empty_values:
                continue
            result += 1
        return result

    def has_min_error(self, fields_with_values: int) -> bool:
        """
        Return True, if a minimum is set and the number of fields with values
        is below that minimum.
        """
        if self.min:
            return fields_with_values < self.min
        else:
            return False

    def has_max_error(self, fields_with_values: int) -> bool:
        """
        Return True, if a maximum is set and the number of fields with values
        exceeds that maximum.
        """
        if self.max:
            return fields_with_values > self.max
        else:
            return False

    def check(self) -> Tuple[bool, bool]:
        """Check whether the limits were exceeded."""
        if not self.min and not self.max:
            return False, False
        fields_with_values = self.fields_with_values()
        min_error = self.has_min_error(fields_with_values)
        max_error = self.has_max_error(fields_with_values)
        return min_error, max_error


class MinMaxRequiredFormMixin(FormMixinBase):
    """
    A mixin that allows setting groups of fields to be required.

    By default, error messages are formatted with the number of fields minimally
    (format kwarg: ``min``) or maximally (``max``) required and a comma
    separated list of those fields (``fields``).

    Attributes:
        - ``minmax_required``: an iterable of dicts, essentially the keyword
          arguments for the FieldGroups
          See 'FieldGroup' constructor args for more details.
        - ``min_error_message`` (str): the default error message for a min error
        - ``max_error_message`` (str): the default error message for a max error

    Example:
        class MyForm(MinMaxRequiredFormMixin, Form):
            spam = forms.IntegerField()
            bacon = forms.IntegerField()
            egg = forms.IntegerField()

            max_error_message = "Too much spam!"
            minmax_required = [{
                'min_fields': 1, 'max_fields': 2,
                'fields': ['spam', 'bacon', 'egg'],
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

        If none of the three fields has data and the user is a viking the form
        will display the min error:
            "Must have at least 1 of Spam, Bacon, Egg, you vile Viking!"
        If all three fields have data, the default max error will be shown
        (as minmax_required does not define a custom error for that group):
            "Too much spam!"
    """

    minmax_required: List[dict]
    min_error_message: str = gettext_lazy("Bitte mindestens {min!s} dieser Felder ausfüllen: {fields}.")
    max_error_message: str = gettext_lazy("Bitte höchstens {max!s} dieser Felder ausfüllen: {fields}.")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.default_error_messages = {"min": self.min_error_message, "max": self.max_error_message}

        super().__init__(*args, **kwargs)

        self._groups = []
        # Check that field names specified in the group_kwargs are present
        # on the form and set the 'required' attribute of those formfields
        # to False.
        for group_kwargs in self.minmax_required or []:
            fields = group_kwargs.get("fields", [])
            if not fields:  # pragma: no cover
                continue
            try:
                for field in fields:
                    self.fields[field].required = False
            except KeyError:
                # At least one field in that group does not have a
                # corresponding formfield; skip the entire group.
                continue
            # TODO: construct the 'error_messages' here and then include the
            #  finished messages in the group_kwargs.
            #  The group should not need to know the form method that creates
            #  the error messages, and we don't need to delay the creation of
            #  those messages until the groups are initialized.
            #  (remember to update the docstrings (f.ex. of get_group_error_messages))
            self._groups.append(group_kwargs)

    def get_groups(self) -> Iterator[FieldGroup]:
        """Instantiate and yield the helper objects."""
        for group_kwargs in self._groups:
            yield FieldGroup(self, **group_kwargs)

    def clean(self) -> dict:
        for group in self.get_groups():
            min_error, max_error = group.check()
            if min_error:
                self.add_group_error("min", group)
            if max_error:
                self.add_group_error("max", group)
        return super().clean()

    def add_group_error(self, error_type: str, group: FieldGroup) -> None:
        self.add_error(None, group.error_messages[error_type])

    def get_error_message_format_kwargs(self, group: FieldGroup) -> dict:
        """Get the string format arguments for the error message template."""
        return {
            "fields": self._get_message_field_names(group),
            "min": group.min or "0",
            "max": group.max or "0",
        }

    def _get_message_field_names(self, group: FieldGroup) -> str:
        """Get a string of the verbose names of the group's fields."""
        return ", ".join(
            self.fields[field_name].label or snake_case_to_spaces(field_name).title()
            for field_name in group.fields
            if field_name in self.fields
        )

    def get_group_error_messages(
        self, group: FieldGroup, error_messages: dict, format_callback: Optional[Union[Callable, str]] = None
    ) -> dict:
        """
        Prepare and format the error messages for the given group.

        If ``format_callback`` is provided (which can be either a callable or
        the name of a method of this form class), it will be called with the
        following args:
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
            error_messages = {k: v.format(**format_kwargs) for k, v in error_messages.items()}
        defaults = self.get_default_error_messages(format_kwargs)
        return {**defaults, **error_messages}

    def get_default_error_messages(self, format_kwargs: dict) -> dict:
        messages = {}
        for error_type in ("min", "max"):
            # noinspection PyUnresolvedReferences
            messages[error_type] = self.default_error_messages[error_type].format(**format_kwargs)
        return messages


class DynamicChoiceFormMixin(FormMixinBase):
    """Set formfield choices after init from keyword arguments."""

    def __init__(self, *args: Any, choices: Optional[dict] = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if choices:  # pragma: no cover
            self.set_choices(choices)

    def set_choices(self, choices: dict) -> None:
        """
        Set choices for choice fields that do not already have choices.

        Args:
            choices (dict): a mapping of choicefield names to its choices.
                django.forms.models.ALL_FIELDS ('__all__') constant can be used
                to set the same choices to all fields that are not mentioned
                in choices.

                django guidelines for choices apply.
                A choice can also be a manager or queryset instance.

        Raises:
             TypeError: when choices argument is not a dictionary instance
        """
        if not isinstance(choices, dict):
            raise TypeError("Expected mapping formfield_name: choices. Got %s." % type(choices))
        for fld_name, fld in self.fields.items():
            if not isinstance(fld, forms.ChoiceField) or fld.choices:
                # Not a choice field or the choices are already set.
                continue
            if self.add_prefix(fld_name) in choices:
                field_choices = choices[self.add_prefix(fld_name)]
            elif forms.ALL_FIELDS in choices:
                field_choices = choices[forms.ALL_FIELDS]
            else:
                continue  # pragma: no cover

            if isinstance(field_choices, BaseManager):
                # model.objects; need to call all() on it.
                field_choices = field_choices.all()
            if isinstance(field_choices, QuerySet):
                # We need 2-tuples (actual value, human readable name):
                fld.choices = [(str(obj.pk), str(obj)) for obj in field_choices]
            else:
                fld.choices = list(field_choices)


class DeleteDuplicatesMixin(ModelFormMixinBase):
    """
    A model form mixin that flags forms for deletion when the form's model
    instance would violate uniqueness.

    Intended to be used with inline formsets such as model admin inlines.
    """

    def validate_unique(self) -> None:
        """
        Call the instance's validate_unique method and plan the deletion of
        this inline formset form, if unique constraints are violated.
        """
        exclude = self._get_validation_exclusions()
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError:
            # Ignore non-unique entries in the same formset.
            self.cleaned_data["DELETE"] = True


class InlineFormBase(DeleteDuplicatesMixin, forms.ModelForm):
    """Base model form class to be used in inline formsets."""

    pass


class DiscogsFormMixin(FormMixinBase):
    """
    A mixin for fields handling data from discogs.

    The form should include two fields:
        - a field that stores the release ID of a record on discogs
        - a field that stores the URL to the page of that record

    This mixin knows these fields through the attributes ``release_id_field_name``
    and ``url_field_name``, and adds validation to both.
    """

    # TODO: all forms using this mixin use the same values for url_field_name and
    #   release_id_field_name => set these values as defaults
    url_field_name: str = ""
    release_id_field_name: str = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.url_field_name in self.fields:
            self.fields[self.url_field_name].validators.append(DiscogsURLValidator())

    def clean(self) -> dict:
        """Validate and clean release_id and discogs_url."""
        if self.url_field_name in self._errors or self.release_id_field_name in self._errors:  # pragma: no cover
            return self.cleaned_data

        # Reminder: cleaned_data['release_id'] could also be integer 0 or None:
        release_id = str(self.cleaned_data.get(self.release_id_field_name, "") or "")
        discogs_url = self.cleaned_data.get(self.url_field_name) or ""

        if not (release_id or discogs_url):
            return self.cleaned_data

        match = re.match(r".*release/(\d+)", discogs_url)
        if match:
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
                self.cleaned_data["release_id"] = release_id
        discogs_url = "https://www.discogs.com/release/" + release_id
        self.cleaned_data["discogs_url"] = discogs_url
        return self.cleaned_data
