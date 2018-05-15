from stdnum import issn

from django.db import models
from django.utils.translation import gettext_lazy
from django.core.validators import EMPTY_VALUES

from .validators import ISSNValidator, ISBNValidator

class StdNumField(models.CharField):
    
    min_length = None
    max_length = None
    
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs['max_length'] if 'max_length' in kwargs else self.max_length
        super().__init__(*args, **kwargs)
        
    def formfield(self, **kwargs):
        kwargs['min_length'] = self.min_length
        kwargs['validators'] = self.default_validators #NOTE: is this actually needed?
        return super().formfield(**kwargs)
        
    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if value not in EMPTY_VALUES:
            value = self._format_value(value)
            setattr(model_instance, self.attname, value)
        return super().pre_save(model_instance, add)
        
    def _format_value(self, value):
        """
        Hook to allow formatting the value according to the chosen ISO.
        """
        return value
    

class ISBNField(StdNumField):
    description = 'Cleaned and validated ISSN string: min length 10, max length 17 (13 digits + dashes/spaces).'
    
    min_length = 10 # ISBN-10
    max_length = 17 # 13 digits of ISBN-13 + four dashes/spaces
    
    default_validators = [ISBNValidator]
    

class ISSNField(StdNumField):
    
    description = 'Cleaned and validated ISSN string of length 8.'
    
    min_length = 7 # ISSN without dash/space and without the check digit: 1234567
    max_length = 9 # ISSN with dash/space and check digit: 1234-5679
    default_validators = [ISSNValidator]
    
    def _format_value(self, value):
        value = issn.compact(value)
        if len(value) == 7:
            # User did not include the check digit
            value += issn.calc_check_digit(value)
        return issn.format(value)
        
