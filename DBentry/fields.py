# ISSN always has 8 digits (the check bit can also be an 'X'), and its pretty version has two groups of 4 digits separated by a hyphen.
# One can freely convert ISBN-10 to ISBN-13 and vice versa and both have pretty versions.
# stdnum.ean does not provide a pretty format for EAN-8, but one can use ISBN-13 formatting for EAN-13.

from functools import partial
from stdnum import issn, isbn, ean

from django.db import models
from django.forms import widgets, fields
from django.core.validators import MaxValueValidator, MinValueValidator

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
    
from django.core.exceptions import ValidationError
import datetime
import re

"""
PartialDate inspired by:
django-partial-date: https://github.com/ktowen/django_partial_date
https://stackoverflow.com/q/2971198
https://stackoverflow.com/a/30186603
"""

class PartialDate(datetime.date):
    
    date_types = {
        'year_month_day': '%Y-%m-%d', 
        'year_month': '%Y-%m', 
        'year': '%Y', 
        'month_day': '%m-%d'
    }
        
    def __new__(cls, year = None, month = None, day = None):
        instance_attrs = {'year': year, 'month': month, 'day': day}
        constructor_args = []
        date_type = []
        
        # Prepare the arguments for the datetime.date constructor 
        # and the attributes that store the passed in parameters (cast to integers if possible).
        for name, value in zip(('year', 'month', 'day'), (year, month, day)):
            if value is None:
                constructor_args.append(1 if name != 'year' else 4)
            else:
                # value can also be '0' at this point
                # the attribute should be None and the constructor arg should be a default
                value = int(value)  # this can raise a ValueError if value cannot be cast to int
                if value == 0:
                    # if it is 0, the partial date should not include it, i.e. don't include it in date_type
                    constructor_args.append(1 if name != 'year' else 4)
                    instance_attrs[name] = None
                else:
                    date_type.append(name)
                    constructor_args.append(value) 
                    instance_attrs[name] = value
            
        date = super().__new__(cls, *constructor_args) # raises a ValueError on invalid dates
        # Set the instance's attributes.
        for k, v in instance_attrs.items():
            # The default attrs year,month,day are not writable.
            setattr(date, '__' + k, v)
        # Get the format string associated with this instance's date type
        if not date_type:
            # This is an 'empty' partial date.
            setattr(date, 'date_type', None)
            setattr(date, 'partial', '')
        else:
            date_type = "_".join(date_type)
            if date_type not in cls.date_types:
                # Note this can only happen if a bad mix of parameters was passed in explicitly.
                # from_string is guaranteed to provide useful parameters 
                # (or it will not call __new__ at all).
                raise ValueError("Unrecognized format: %s" % date_type)
            setattr(date, 'date_type', date_type)
            setattr(date, 'partial', date.strftime(cls.date_types[date_type]))
        return date        
        
    def __str__(self):
        return self.partial
        
    def __iter__(self):
        for attr in ('__year', '__month', '__day'):
            yield getattr(self, attr, None)
            
    def __len__(self):
        # This allows the MaxLengthValidator of CharField to test the length of the PartialDate
        return len(self.partial)
        
    def __eq__(self, other):
        if isinstance(other, str):
            return self.__str__().__eq__(other)
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
        
    
class PartialDateWidget(widgets.MultiWidget):
    
    def __init__(self, **kwargs):
        _widgets = [
            widgets.NumberInput(), 
            widgets.NumberInput(), 
            widgets.NumberInput(), 
        ]  
        super().__init__(_widgets, **kwargs)
        
    def decompress(self, value):
        if isinstance(value, PartialDate):
            return list(value)
        return [None, None, None]

class PartialDateFormField(fields.MultiValueField):
    
    default_error_messages = fields.DateField.default_error_messages
    default_error_messages['invalid_combo'] = "Ungültige Kombination von Jahr und Tag."
    
    def __init__(self, **kwargs):
        _fields = [
            fields.IntegerField(label = 'Jahr', required = False), 
            fields.IntegerField(label = 'Monat', required = False), 
            fields.IntegerField(label = 'Tag', required = False), 
        ]
        if 'max_length' in kwargs:
            # super(PartialDateField).formfield (i.e. CharField)
            # adds a max_length kwarg that MultiValueField does not handle
            del kwargs['max_length']
        if 'widget' in kwargs: del kwargs['widget']
        super().__init__(_fields, widget = PartialDateWidget, require_all_fields = False, **kwargs)
        
    def compress(self, data_list):
        try:
            return PartialDate(*data_list)
        except ValueError:
            if len(data_list) == 3 and data_list[0] and data_list[-1] and not data_list[1]: 
                # Attempting to build a partial date out of year and day.
                raise ValidationError(self.error_messages['invalid_combo'], code='invalid_combo')
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        
class PartialDateField(models.CharField):
    
    default_error_messages = models.DateField.default_error_messages
    default_error_messages['invalid_combo'] = "Ungültige Kombination von Jahr und Tag."
    
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
        return self.to_python(value).partial
        
    def from_db_value(self, value, expression, connection):
        return PartialDate.from_string(value)
        
    def formfield(self, **kwargs):
        return super().formfield(form_class = PartialDateFormField, **kwargs)
