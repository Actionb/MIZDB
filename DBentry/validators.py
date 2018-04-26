from stdnum import issn

from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy

class StdValidationError(ValidationError):
    message = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(self.message, *args, **kwargs)

class InvalidLength(StdValidationError):
    message = gettext_lazy('The number has an invalid length.')

class InvalidFormat(StdValidationError):
    message = gettext_lazy('The number has an invalid format.')

class InvalidChecksum(StdValidationError):
    message = gettext_lazy("The number's checksum or check digit is invalid.")

class InvalidComponent(StdValidationError):
    message = gettext_lazy("One of the parts of the number are invalid or unknown.")

def _validate(std, number):
    from stdnum import exceptions
    try:
        std.validate(number)
    except exceptions.InvalidLength:
        raise InvalidLength()
    except exceptions.InvalidFormat:
        raise InvalidFormat()
    except exceptions.InvalidChecksum:
        raise InvalidChecksum()
    except exceptions.InvalidComponent:
        raise InvalidComponent()
    return True
    
def ISBNValidator(raw_isbn):
    return True

def ISSNValidator(raw_issn):
    raw_issn = issn.compact(raw_issn)
    if len(raw_issn) == 7:
        # User did not include the check digit
        if raw_issn.isnumeric():
            raw_issn += issn.calc_check_digit(raw_issn)
        else:
            raise InvalidChecksum()
    return _validate(issn, raw_issn)
        
        
