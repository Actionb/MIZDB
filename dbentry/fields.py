import datetime
import re
from functools import total_ordering
from stdnum import issn, isbn, ean

from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.forms import widgets, fields
from django.utils import formats

from dbentry.validators import ISSNValidator, ISBNValidator, EANValidator
# FIXME: PartialDate: changelist queries (using the advanced search form formfields) require a year value.


class YearField(models.IntegerField):
    """
    An IntegerField that validates against min and max values for year numbers.
    """

    MAX_YEAR = 3000
    MIN_YEAR = 1800

    def formfield(self, **kwargs):
        kwargs['validators'] = [
            MaxValueValidator(self.MAX_YEAR),
            MinValueValidator(self.MIN_YEAR)
        ]
        return super().formfield(**kwargs)


class StdNumWidget(widgets.TextInput):
    """A TextInput widget that formats its value according to a format_callback."""

    def __init__(self, format_callback=None, *args, **kwargs):
        self.format_callback = format_callback
        super().__init__(*args, **kwargs)

    def format_value(self, value):
        if not value or self.format_callback is None:
            return value
        # Render the value in a pretty format
        return self.format_callback(value)


class StdNumFormField(fields.CharField):
    """
    Base formfield for standard number formfields.

    Takes one additional positional keyword:
        stdnum: the module of the stdnum library that implements validation and
            formatting of the desired kind of standard number
    """

    def __init__(self, stdnum, *args, **kwargs):
        self.stdnum = stdnum
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """Return the compactified python value."""
        value = super().to_python(value)
        return self.stdnum.compact(value)


class ISBNFormField(StdNumFormField):

    def to_python(self, value):
        value = super().to_python(value)
        if value not in self.empty_values and isbn.isbn_type(value) == 'ISBN10':
            # Cast the ISBN10 into a ISBN13, so value can match the initial
            # value (which is always ISBN13).
            value = isbn.to_isbn13(value)
        return value


class ISSNFormField(StdNumFormField):

    def to_python(self, value):
        value = super().to_python(value)
        if value not in self.empty_values and len(value) == 13:
            # Compactified value is possibly a EAN-13 number.
            # Retrieve the ISSN number.
            value = value[3:-3]
            value += issn.calc_check_digit(value)
        return value


class StdNumField(models.CharField):
    """
    Base model field for standard number fields.

    Attributes:
        stdnum: the module of the stdnum library that implements validation and
            formatting of the desired kind of standard number
        min_length (int): minimal length of the number.
            Only used in formfield validation.
        max_length (int): The maximum length (in characters) of the field.
    """
    stdnum = None
    min_length = None
    max_length = None

    def __init__(self, *args, **kwargs):
        if self.max_length and 'max_length' not in kwargs:
            kwargs['max_length'] = self.max_length
        super().__init__(*args, **kwargs)

    def formfield(self, widget=None, **kwargs):
        defaults = {
            'min_length': self.min_length,
            'stdnum': self.stdnum,
            'form_class': StdNumFormField,
            # Pass this ModelField's validators to the FormField for
            # form-based validation.
            'validators': self.default_validators,
        }
        kwargs = {**defaults, **kwargs}

        widget_class = None
        # Pass the format callback function to the widget for a
        # prettier display of the value.
        widget_kwargs = {'format_callback': self.get_format_callback()}
        if widget:
            # django-admin will pass its own widget instance to formfield()
            # (or whatever the ModelAdmins.formfield_overrides sets).
            # This means losing the StdNumWidget and its prettier output.
            if isinstance(widget, type):
                widget_class = widget
            else:
                widget_kwargs['attrs'] = getattr(widget, 'attrs', None)
                widget_class = widget.__class__
            if not issubclass(widget_class, StdNumWidget):
                widget_class = StdNumWidget
        else:
            widget_class = StdNumWidget
        kwargs['widget'] = widget_class(**widget_kwargs)
        return super().formfield(**kwargs)

    def get_format_callback(self):
        if hasattr(self.stdnum, 'format'):
            return self.stdnum.format
        # Fallback for ean stdnum which does not have a format function.
        return self.stdnum.compact

    def to_python(self, value):
        # In order to deny querying and saving with invalid values, we have to
        # call run_validators.
        # Saving a model instance will not cause the validators to be tested!
        if value not in self.empty_values:
            value = self.stdnum.compact(value)
        self.run_validators(value)
        return value


class ISBNField(StdNumField):
    stdnum = isbn
    min_length = 10  # ISBN-10 without dashes/spaces
    max_length = 17  # ISBN-13 with four dashes/spaces
    default_validators = [ISBNValidator]
    description = ('Cleaned and validated ISBN string: min length 10 '
        '(ISBN-10), max length 17 (13 digits + dashes/spaces).')

    def to_python(self, value):
        # Save the values as ISBN-13.
        if value in self.empty_values:
            return value
        value = super().to_python(value)
        return isbn.to_isbn13(value)

    def get_format_callback(self):
        def _format(value):
            """Return a well formatted ISBN13."""
            if value in self.empty_values:
                return value
            return isbn.format(value, convert=True)
        return _format

    def formfield(self, **kwargs):
        defaults = {'form_class': ISBNFormField}
        return super().formfield(**{**defaults, **kwargs})


class ISSNField(StdNumField):
    stdnum = issn
    min_length = 8  # ISSN without dash/space
    max_length = 9  # ISSN with dash/space
    default_validators = [ISSNValidator]
    description = 'Cleaned and validated ISSN string of length 8.'

    def formfield(self, **kwargs):
        defaults = {
            # Allow for EAN-13 with dashes/spaces as form data
            'max_length': 17,
            'form_class': ISSNFormField
        }
        return super().formfield(**{**defaults, **kwargs})


class EANField(StdNumField):
    stdnum = ean  # Note that the ean module does not have a 'format' function
    min_length = 8  # EAN-8
    max_length = 17  # EAN-13 with four dashes/spaces
    default_validators = [EANValidator]
    description = ('Cleaned and validated EAN string: min length 8 (EAN-8), '
        'max length 17 (13 digits + dashes/spaces).')


"""
PartialDate inspired by:
django-partial-date: https://github.com/ktowen/django_partial_date
https://stackoverflow.com/q/2971198
https://stackoverflow.com/a/30186603
"""
@total_ordering
class PartialDate(datetime.date):
    """A datetime.date that allows constructor arguments to be optional."""

    db_value_template = '{year!s:0>4}-{month!s:0>2}-{day!s:0>2}'

    def __new__(cls, year=None, month=None, day=None):
        # Default values for the instance's attributes
        instance_attrs = {'year': None, 'month': None, 'day': None}
        # Default values for the datetime.date constructor
        constructor_kwargs = {'year': 4, 'month': 1, 'day': 1}
        date_format = []
        iterator = zip(
            ('day', 'month', 'year'), (day, month, year), ('%d', '%B', '%Y')
        )
        for name, value, format in iterator:
            if value is None:
                continue
            value = int(value)
            if value != 0:
                constructor_kwargs[name] = value
                instance_attrs[name] = value
                date_format.append(format)
        # Call the datetime.date constructor. If the date is invalid,
        # a ValueError will be raised.
        date = super().__new__(cls, **constructor_kwargs)
        # Set the instance's attributes.
        for k, v in instance_attrs.items():
            # The default attrs year,month,day are not writable.
            setattr(date, '__' + k, v)
        if not date_format:
            # This is an 'empty' partial date.
            setattr(date, 'date_format', '')
        else:
            setattr(date, 'date_format', ' '.join(date_format))
        return date

    @classmethod
    def from_string(cls, date):
        """Create a PartialDate from the string 'date'."""
        regex = re.compile(
            r'^(?P<year>\d{4})?(?:-?(?P<month>\d{1,2}))?(?:-(?P<day>\d{1,2}))?$'
        )
        match = regex.match(date)
        if match:
            return cls.__new__(cls, **match.groupdict())
        raise ValueError("Invalid format: 'YYYY-MM-DD' expected.")

    @classmethod
    def from_date(cls, date):
        """Create a PartialDate from a datetime.date instance."""
        year, month, day, *_ = date.timetuple()
        return cls.__new__(cls, year, month, day)

    @property
    def db_value(self):
        """Return a string of format 'YYYY-MM-DD' to store in the database."""
        format_kwargs = {'year': 0, 'month': 0, 'day': 0}
        for attr in ('year', 'month', 'day'):
            value = getattr(self, '__' + attr, False)
            if value:
                format_kwargs[attr] = value
        return self.db_value_template.format(**format_kwargs)

    def __str__(self):
        return self.strftime(self.date_format)

    def localize(self):
        if self.date_format:
            # Fun fact: python's format code for month textual long is %B.
            # django's is %F (%B isn't even implemented?).
            return formats.date_format(
                self, self.date_format.replace('%B', '%F').replace('%', ''))
        return ''

    def __iter__(self):
        for attr in ('__year', '__month', '__day'):
            yield getattr(self, attr, None)

    def __len__(self):
        """Return the length of the string value to be stored in the database."""
        # This allows the MaxLengthValidator of CharField to test the length of
        # the PartialDate.
        return len(self.db_value)

    def __bool__(self):
        """Return False if this PartialDate is made of only default values."""
        # Base 'truthiness' of a PartialDate on it having a non-empty
        # date_format. Empty PartialDates thus are recognized as False.
        return bool(self.date_format)

    def __eq__(self, other):
        if bool(self) != bool(other):
            # Comparing an empty date with any non-empty string/date or
            # comparing any non-empty date with an empty string/date.
            return False
        if not bool(self) and not bool(other):
            # Comparing an empty date with an empty string/date.
            return True
        # Comparing an actual date with an actual string/date.
        if isinstance(other, str):
            try:
                other = self.from_string(other)
            except ValueError:
                return False
        return super().__eq__(other)

    def __gt__(self, other):
        if isinstance(other, str):
            return self.__str__().__gt__(other)
        return super().__gt__(other)


class PartialDateWidget(widgets.MultiWidget):
    """Default widget for the PartialDateFormField."""

    def __init__(self, **kwargs):
        if 'widgets' in kwargs:
            _widgets = kwargs.pop('widgets')
        else:
            _widgets = []
            for placeholder in ('Jahr', 'Monat', 'Tag'):
                attrs = {'placeholder': placeholder}
                if placeholder != 'Tag':
                    style = {'style': 'width:70px; margin-right:10px;'}
                else:
                    style = {'style': 'width:70px;'}
                attrs.update(style)
                _widgets.append(widgets.NumberInput(attrs=attrs))
        super().__init__(_widgets, **kwargs)

    def decompress(self, value):
        if isinstance(value, PartialDate):
            return list(value)
        return [None, None, None]


class PartialDateFormField(fields.MultiValueField):
    """Default form field for PartialDateField model field."""

    default_error_messages = fields.DateField.default_error_messages

    def __init__(self, **kwargs):
        if 'fields' in kwargs:
            _fields = kwargs.pop('fields')
        else:
            _fields = [fields.IntegerField(required=False)] * 3
        if 'max_length' in kwargs:
            # super(PartialDateField).formfield (i.e. CharField.formfield)
            # adds a max_length kwarg that MultiValueField does not handle
            del kwargs['max_length']
        widget = PartialDateWidget
        if 'widget' in kwargs:
            # django admin will try to instantiate this formfield with an
            # AdminTextInputWidget.
            # Accept widget from the kwargs as a replacement if it's either
            # a subclass or an instance of PartialDateWidget.
            kwarg_widget = kwargs.pop('widget')
            is_pd_widget = (
                isinstance(kwarg_widget, type)
                and issubclass(kwarg_widget, PartialDateWidget)
            )
            if (isinstance(kwarg_widget, PartialDateWidget)
                    or is_pd_widget):
                widget = kwarg_widget
        super().__init__(
            _fields, widget=widget, require_all_fields=False, **kwargs
        )

    def compress(self, data_list):
        try:
            return PartialDate(*data_list)
        except ValueError:
            raise ValidationError(
                self.error_messages['invalid'], code='invalid'
            )


class PartialDateField(models.CharField):
    """Model field that handles PartialDate instances."""

    default_error_messages = models.DateField.default_error_messages
    help_text = "Teilweise Angaben sind erlaubt (z.B. Jahr & Monat aber ohne Tag)."

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10  # digits: 4 year, 2 month, 2 day, 2 dashes
        if 'null' not in kwargs:
            kwargs['null'] = False
        if 'blank' not in kwargs:
            kwargs['blank'] = True
        if 'help_text' not in kwargs:
            kwargs['help_text'] = self.help_text
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return PartialDate()
        if isinstance(value, str):
            try:
                pd = PartialDate.from_string(value)
            except ValueError:
                # Either from_string could not match its regex or
                # the date produced is invalid (e.g. 02-31)
                raise ValidationError(
                    self.error_messages['invalid_date'],
                    code='invalid_date',
                    params={'value': value},
                )
            return pd
        elif isinstance(value, PartialDate):
            return value
        elif isinstance(value, datetime.date):
            return PartialDate.from_date(value)

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return self.to_python(value).db_value

    def from_db_value(self, value, expression, connection):
        return PartialDate.from_string(value)

    def formfield(self, **kwargs):
        return super().formfield(form_class=PartialDateFormField, **kwargs)
