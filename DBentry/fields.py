# ISSN always has 8 digits (the check bit can also be an 'X'), and its pretty version has two groups of 4 digits separated by a hyphen.
# One can freely convert ISBN-10 to ISBN-13 and vice versa and both have pretty versions.
# stdnum.ean does not provide a pretty format for EAN-8, but one can use ISBN-13 formatting for EAN-13.


import datetime
import re
from functools import partial
from stdnum import issn, isbn, ean

from django.db import models
from django.forms import widgets, fields
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.utils import formats

from DBentry.validators import ISSNValidator, ISBNValidator, EANValidator

class YearField(models.IntegerField):
    
    def formfield(self, **kwargs):
        from DBentry.constants import MIN_JAHR, MAX_JAHR
        kwargs['validators'] = [MaxValueValidator(MAX_JAHR),MinValueValidator(MIN_JAHR)]
        return super().formfield(**kwargs)
        
class StdNumWidget(widgets.TextInput):
    
    def __init__(self, format_callback = None, *args, **kwargs):
        self.format_callback = format_callback
        super().__init__(*args, **kwargs)
    
    def format_value(self, value):
        if value is None or self.format_callback is None:
            return value
        # Render the value in a pretty format
        return self.format_callback(value)
        
class StdNumFormField(fields.CharField):
    
    def __init__(self, stdnum, *args, **kwargs):
        self.stdnum = stdnum
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        value = super().to_python(value)
        if self.stdnum == isbn and isbn.isbn_type(value) == 'ISBN10':
            # cast the ISBN10 into a ISBN13, so value can match the initial value (which is always ISBN13)
            value = isbn.to_isbn13(value)
        # To ensure that an initial compact value does not differ from a data formatted value, compact the data value. See FormField.has_changed
        return self.stdnum.compact(value)

class StdNumField(models.CharField):
    stdnum = None
    min_length = None
    max_length = None
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs['max_length'] if 'max_length' in kwargs else self.max_length
        super().__init__(*args, **kwargs)
        
    def formfield(self, **kwargs):
        kwargs['min_length'] = self.min_length # max_length is added by CharField.formfield
        kwargs['stdnum'] = self.stdnum
        kwargs['form_class'] = StdNumFormField
        # Pass this ModelField's validators to the FormField for form-based validation.
        kwargs['validators'] = self.default_validators
        # Pass the format callback function to the widget for a prettier display of the value
        kwargs['widget'] = StdNumWidget(format_callback = self.get_format_callback())
        return super().formfield(**kwargs)
        
    def get_format_callback(self):
        if hasattr(self.stdnum, 'format'):
            return self.stdnum.format
        # Fallback for ean stdnum which does not have a format function
        return self.stdnum.compact

    def to_python(self, value):
        # In order to deny querying and saving with invalid values, we have to call run_validators.
        # Saving a model instance will not cause the validators to be tested!
        value = self.stdnum.compact(value)
        self.run_validators(value)
        return value
        
class ISBNField(StdNumField):
    description = 'Cleaned and validated ISBN string: min length 10 (ISBN-10), max length 17 (13 digits + dashes/spaces).'
    
    stdnum = isbn
    min_length = 10 # ISBN-10 without dashes/spaces
    max_length = 17 # ISBN-13 with four dashes/spaces
    
    default_validators = [ISBNValidator]
    
    def to_python(self, value):
        # Save the values as ISBN-13
        value = super().to_python(value)
        return isbn.to_isbn13(value)
        
    def get_format_callback(self):
        return partial(isbn.format, convert=True)
        

class ISSNField(StdNumField):
    description = 'Cleaned and validated ISSN string of length 8.'
    
    stdnum = issn
    min_length = 8 # ISSN without dash/space
    max_length = 9 # ISSN with dash/space
    default_validators = [ISSNValidator]
        
class EANField(StdNumField):
    description = 'Cleaned and validated EAN string: min length 8 (EAN-8), max length 17 (13 digits + dashes/spaces).'
    
    stdnum = ean
    min_length = 8  # EAN-8
    max_length = 17 # EAN-13 with four dashes/spaces
    default_validators = [EANValidator]
    
"""
PartialDate inspired by:
django-partial-date: https://github.com/ktowen/django_partial_date
https://stackoverflow.com/q/2971198
https://stackoverflow.com/a/30186603
"""

class PartialDate(datetime.date):
    
    db_value_template = '{year!s:0>4}-{month!s:0>2}-{day!s:0>2}'
    
    def __new__(cls, year = None, month = None, day = None):
        # Default values for the instance's attributes
        instance_attrs = {'year': None, 'month': None, 'day': None}
        # Default values for the datetime.date constructor
        constructor_kwargs = {'year': 4, 'month': 1, 'day': 1}
        date_format = []
        for name, value, format in zip(
                ('day', 'month', 'year'), (day, month, year), ('%d', '%b', '%Y') #TODO: %d. (dot) for 20. May 2019?
            ):
            if value is None:
                continue
            value = int(value)
            if value != 0:
                constructor_kwargs[name] =  value
                instance_attrs[name] = value
                date_format.append(format)
            
        date = super().__new__(cls, **constructor_kwargs) # raises a ValueError on invalid dates
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
        regex =  re.compile(r'^(?P<year>\d{4})?(?:-?(?P<month>\d{1,2}))?(?:-(?P<day>\d{1,2}))?$')
        match = regex.match(date)
        if match:
            return cls.__new__(cls, **match.groupdict())
        raise ValueError("Invalid format.")
            
    @classmethod
    def from_date(cls, date):
        year, month, day, *_ = date.timetuple()
        return cls.__new__(cls, year, month, day)
        
    @property
    def db_value(self):
        """
        Returns a string of format 'YYYY-MM-DD' to store in the database.
        """
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
            return formats.date_format(self, self.date_format.replace('%', ''))
        return ''
        
    def __iter__(self):
        for attr in ('__year', '__month', '__day'):
            yield getattr(self, attr, None)
            
    def __len__(self):
        # This allows the MaxLengthValidator of CharField to test the length of the PartialDate
        return len(self.db_value)
        
    def __eq__(self, other):
        if isinstance(other, str):
            try:
                other = self.from_string(other)
            except:
                return False
        return super().__eq__(other)
        
#TODO: rich comparison
#    def __gt__(self, other):
#        if isinstance(other, str):
#            return self.__str__().__gt__(other)
#        return super().__gt__(other)
#        
#    def __ge__(self, other):
#        if isinstance(other, str):
#            return self.__str__().__ge__(other)
#        return super().__ge__(other)        
    
class PartialDateWidget(widgets.MultiWidget):
    
    def __init__(self, **kwargs):
        style = {'style':'width:70px; margin-right:10px;'}
        _widgets = []
        for placeholder in ('Jahr', 'Monat', 'Tag'):
            attrs = {'placeholder': placeholder}
            attrs.update(style)
            _widgets.append(widgets.NumberInput(attrs = attrs))
        super().__init__(_widgets, **kwargs)
        
    def decompress(self, value):
        if isinstance(value, PartialDate):
            return list(value)
        return [None, None, None]

class PartialDateFormField(fields.MultiValueField):
    
    default_error_messages = fields.DateField.default_error_messages
    
    def __init__(self, **kwargs):
        _fields = [
            fields.IntegerField(), 
            fields.IntegerField(), 
            fields.IntegerField(), 
        ]
        if 'max_length' in kwargs:
            # super(PartialDateField).formfield (i.e. CharField.formfield)
            # adds a max_length kwarg that MultiValueField does not handle
            del kwargs['max_length']
            
        widget = PartialDateWidget
        if 'widget' in kwargs: 
            # django admin will try to instantiate this formfield with a AdminTextInputWidget
            kwarg_widget = kwargs.pop('widget')
            if (isinstance(kwarg_widget, type) and issubclass(kwarg_widget, PartialDateWidget)) or \
                isinstance(kwarg_widget, PartialDateWidget):
                    # Accept widget from the kwargs as a replacement if it's either 
                    # a subclass or an instance of PartialDateWidget.
                widget = kwarg_widget
        super().__init__(_fields, widget = widget, **kwargs)
        
    def compress(self, data_list):
        try:
            return PartialDate(*data_list)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        
class PartialDateField(models.CharField):
    
    default_error_messages = models.DateField.default_error_messages
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10 # digits: 4 year, 2 month, 2 day, 2 dashes
        if 'null' not in kwargs: kwargs['null'] = False
        if 'blank' not in kwargs: kwargs['blank'] = True
        super().__init__(*args, **kwargs)
    
    def to_python(self, value):
        if not value:
            return PartialDate() #TODO: or return None?
        if isinstance(value, str):
            try:
                pd = PartialDate.from_string(value)
            except ValueError:
                # TODO: if we raised a different kind of exception 
                # in from_string we could differentiate between
                # - invalid format for regex (--> code 'invalid')
                # - invalid date (--> code 'invalid_date')
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
        return super().formfield(form_class = PartialDateFormField, **kwargs)
