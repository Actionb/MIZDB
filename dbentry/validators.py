import re
from typing import Any

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy
from stdnum import ean, isbn, issn
from stdnum import exceptions as stdnum_exceptions


class MsgValidationError(ValidationError):
    """Validation error with a preset message."""

    message = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # ValidationError requires one positional argument 'message'
        super().__init__(self.message, *args, **kwargs)


class InvalidLength(MsgValidationError):
    message = gettext_lazy("The number has an invalid length.")


class InvalidFormat(MsgValidationError):
    message = gettext_lazy("The number has an invalid format.")


class InvalidChecksum(MsgValidationError):
    message = gettext_lazy("The number's checksum or check digit is invalid.")


class InvalidComponent(MsgValidationError):
    message = gettext_lazy("One of the parts of the number are invalid or unknown.")


def _validate(stdnum_module: Any, number: str) -> bool:
    """
    Validate ``number`` using the validate function of the given standard
    number module ``std``.

    Re-raise the standard number exceptions as django.ValidationErrors.
    """
    try:
        return bool(stdnum_module.validate(number))
    except stdnum_exceptions.InvalidLength:
        raise InvalidLength()
    except stdnum_exceptions.InvalidFormat:
        raise InvalidFormat()
    except stdnum_exceptions.InvalidChecksum:
        raise InvalidChecksum()
    except stdnum_exceptions.InvalidComponent:
        raise InvalidComponent()


# noinspection PyPep8Naming
def ISBNValidator(raw_isbn: str) -> bool:
    return _validate(isbn, raw_isbn)


# noinspection PyPep8Naming
def ISSNValidator(raw_issn: str) -> bool:
    return _validate(issn, raw_issn)


# noinspection PyPep8Naming
def EANValidator(raw_ean: str) -> bool:
    return _validate(ean, raw_ean)


class DiscogsURLValidator(RegexValidator):
    """Validator that checks that the given URL's host is 'discogs.com'."""

    regex = r"^([a-z][a-z0-9+\-.]*://)?(www.)?discogs.com"
    message = "Bitte nur Adressen von discogs.com eingeben."
    code = "discogs"


class DiscogsMasterReleaseValidator(RegexValidator):
    """Validator that checks that the value isn't a discogs master release."""

    regex = r"/master/(\d+)"
    message = "Bitte keine Adressen von Master-Releases eingeben."
    code = "master_release"
    inverse_match = True


class DNBURLValidator(RegexValidator):
    """
    RegexValidator for URLs of the German national library.

    This validator captures the GND ID in the first group for a given valid URL.
    """

    regex = re.compile(r".*(?:d-nb.info?|portal.dnb.de?)/.*(?:gnd/?|nid%3D?)(\w+)")
    message = "Bitte nur Adressen der DNB eingeben (d-nb.info oder portal.dnb.de)."
    code = "dnb"
