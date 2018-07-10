from stdnum import issn, isbn, ean
from stdnum.util import clean

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy

class StdValidationError(ValidationError):
    message = None
    
    def __init__(self, *args, **kwargs):
        # ValidationError requires one positional argument 'message'
        super().__init__(self.message, *args, **kwargs)

class InvalidLength(StdValidationError):
    message = gettext_lazy('The number has an invalid length.')

class InvalidFormat(StdValidationError):
    message = gettext_lazy('The number has an invalid format.')

class InvalidChecksum(StdValidationError):
    message = gettext_lazy("The number's checksum or check digit is invalid.")

class InvalidComponent(StdValidationError):
    message = gettext_lazy("One of the parts of the number are invalid or unknown.")

def _add_check_digit(std, number, min_length):
    number = std.compact(number)
    if len(number) == min_length:
        # User did not include the check digit
        if number.isnumeric():
            number += std.calc_check_digit(number)
        else:
            raise InvalidComponent()
    return number

def _validate(std, number, min_length=None):
    from stdnum import exceptions
    if min_length:
        number = _add_check_digit(std, number, min_length)
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
    raw_isbn = clean(raw_isbn, ' -').strip().upper()
    if raw_isbn.isnumeric():
        if len(raw_isbn) == 9:
            raw_isbn += isbn._calc_isbn10_check_digit(raw_isbn)
        elif len(raw_isbn) == 12:
            raw_isbn += ean.calc_check_digit(raw_isbn)
    return _validate(isbn, raw_isbn)

def ISSNValidator(raw_issn):
    return _validate(issn, raw_issn, 7)
    
def EANValidator(raw_ean):
    return _validate(ean, raw_ean, 7)
    
        
        
