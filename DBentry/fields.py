# ISSN always has 8 digits (the check bit can also be an 'X'), and its pretty version has two groups of 4 digits separated by a hyphen.
# One can freely convert ISBN-10 to ISBN-13 and vice versa and both have pretty versions.
# stdnum.ean does not provide a pretty format for EAN-8, but one can use ISBN-13 formatting for EAN-13.

#TODO: use get_prep_lookup?

from stdnum import issn, isbn, ean

from django.db import models
from django.core.validators import EMPTY_VALUES, MaxValueValidator, MinValueValidator
from .validators import ISSNValidator, ISBNValidator, EANValidator

class YearField(models.IntegerField):
    
    def formfield(self, **kwargs):
        from DBentry.constants import MIN_JAHR, MAX_JAHR
        kwargs['validators'] = [MaxValueValidator(MAX_JAHR),MinValueValidator(MIN_JAHR)]
        return super().formfield(**kwargs)

class StdNumField(models.CharField):
    
    stdnum = None
    min_length = None
    max_length = None
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs['max_length'] if 'max_length' in kwargs else self.max_length
        super().__init__(*args, **kwargs)
        
    def formfield(self, **kwargs):
        kwargs['min_length'] = self.min_length
        kwargs['validators'] = self.default_validators
        return super().formfield(**kwargs)
        
    def get_prep_value(self, value):
        # Return the formatted value for the queries.
        # When saving, pre_save is called before this, but we still need to return the formatted value for ordinary queries.
        return self._format_value(value)
        
    def pre_save(self, model_instance, add):
        # Update the model_instance's value for this field with the formatted value.
        # The SQL compiler uses this method to ask for the right value just before saving,
        # but the compiler does not update the (already created but not saved) instance.
        # Without this adjustment and without calling instance.refresh_from_db(), you may end up with an instance displaying the 'unformatted' value 
        # while the db has stored the formatted one.
        value = super().pre_save(model_instance, add)
        if value not in EMPTY_VALUES:
            value = self._format_value(value)
            setattr(model_instance, self.attname, value)
        return value        
        
    def _add_check_digit(self, value):
        """
        Adds the check digit if it was missing.
        """
        value = self.stdnum.compact(value)
        if len(value) == self.min_length:    
            # User did not include the check digit
            value += self.stdnum.calc_check_digit(value)
        return value
        
    def _format_value(self, value):
        """
        Hook to allow formatting the value according to the chosen ISO.
        """
        # Run the validators before doing anything to value, no point formatting invalid input.
        self.run_validators(value)
        
        # See if value is missing a check digit and add it if necessary
        #TODO: try to streamline this a bit more, we are validating and formatting the value like three times in one process
        try:
            value = self._add_check_digit(value)
        except AttributeError:
            # stdnum module didnt have either a compact or a calc_check_digit attribute
            pass
        if hasattr(self.stdnum, 'format'):
            return self.stdnum.format(value)
        elif hasattr(self.stdnum, 'compact'):
            return self.stdnum.compact(value)
        else:
            return value
    

class ISBNField(StdNumField):
    description = 'Cleaned and validated ISBN string: min length 9 (ISBN-10 w/o check digit), max length 17 (13 digits + dashes/spaces).'
    
    stdnum = isbn
    min_length = 9 # ISBN-10 without check-digit
    max_length = 17 # ISBN-13 with four dashes/spaces and check digit
    
    default_validators = [ISBNValidator]
        
    def _format_value(self, value):
        from stdnum.util import clean
        value = clean(value, ' -').strip().upper()
        if value.isnumeric():
            if len(value) == 9:
                value += isbn._calc_isbn10_check_digit(value)
            elif len(value) == 12:
                value += ean.calc_check_digit(value)
        return isbn.format(value, convert = True) # convert to ISBN-13
    

class ISSNField(StdNumField):
    description = 'Cleaned and validated ISSN string of length 8.'
    
    stdnum = issn
    min_length = 7 # ISSN without check digit: 1234567
    max_length = 9 # ISSN with dash/space and check digit: 1234-5679
    default_validators = [ISSNValidator]
        
class EANField(StdNumField):
    description = 'Cleaned and validated EAN string: min length 7 (EAN-8 w/o check digit), max length 17 (13 digits + dashes/spaces).'
    
    stdnum = ean
    min_length = 7  # EAN-8 without check digit
    max_length = 17 # EAN-13 with four dashes/spaces and check digit
    default_validators = [EANValidator]
