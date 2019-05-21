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
    
class PartialDate(object):
    pass
    
class PartialDateWidget(widgets.MultiWidget):
    pass

class PartialDateFormField(fields.MultiValueField):
    pass
    
class PartialDateField(models.CharField):
    
    def to_python(self, value):
        pass
    
    def get_prep_value(self, value):
        pass
    
    def from_db_value(self, value, expression, connection):
        pass
        
    def formfield(self, **kwargs):
        pass
