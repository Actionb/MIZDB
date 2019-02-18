import re

from stdnum import issn, isbn, ean
from stdnum import exceptions as stdnum_exceptions

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy

from DBentry.constants import discogs_release_id_pattern

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


def _validate(std, number):
    # Reraise the exceptions as django.ValidationErrors
    try:
        std.validate(number)
    except stdnum_exceptions.InvalidLength:
        raise InvalidLength()
    except stdnum_exceptions.InvalidFormat:
        raise InvalidFormat()
    except stdnum_exceptions.InvalidChecksum:
        raise InvalidChecksum()
    except stdnum_exceptions.InvalidComponent:
        raise InvalidComponent()
    return True
    
def ISBNValidator(raw_isbn):
    return _validate(isbn, raw_isbn)

def ISSNValidator(raw_issn):
    return _validate(issn, raw_issn)
    
def EANValidator(raw_ean):
    return _validate(ean, raw_ean)
    
class DiscogsURLValidator(RegexValidator):
    regex = re.compile(discogs_release_id_pattern)
    message = "Bitte nur Adressen von discogs.com eingeben."
    code = "discogs"
        
        
