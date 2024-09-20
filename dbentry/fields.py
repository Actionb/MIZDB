import datetime
import re
from functools import total_ordering
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Type, Union

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import formats
from stdnum import ean, isbn, issn

from dbentry.site.renderer import IS_INVALID_CLASS
from dbentry.validators import EANValidator, ISBNValidator, ISSNValidator

StrOrInt = Optional[Union[str, int]]


class YearField(models.IntegerField):
    """An IntegerField that validates against min and max values for year numbers."""

    MAX_YEAR: int = 3000
    MIN_YEAR: int = 1800

    def formfield(self, **kwargs: Any) -> forms.Field:
        kwargs["validators"] = [MaxValueValidator(self.MAX_YEAR), MinValueValidator(self.MIN_YEAR)]
        return super().formfield(**kwargs)


class StdNumWidget(forms.TextInput):
    """
    A TextInput widget that uses 'prettier' standard number formatting to
    render its value.
    """

    def __init__(self, format_callback: Optional[Callable[[str], str]] = None, *args: Any, **kwargs: Any) -> None:
        """
        Instantiate the widget.

        Args:
            format_callback: callable that takes the plain value and formats it
            args: positional arguments for TextInput
            kwargs: keyword arguments for TextInput
        """
        self.format_callback = format_callback
        super().__init__(*args, **kwargs)

    def format_value(self, value: str) -> str:
        if not value or self.format_callback is None:
            return value
        # Render the value in a pretty format
        return self.format_callback(value)


class StdNumFormField(forms.CharField):
    """
    The base formfield for standard number formfields.

    Compacts input values (removing whitespaces, hyphens, etc.) by using the
    'compact' function of the assigned standard number module.
    """

    def __init__(self, stdnum: Any, *args: Any, **kwargs: Any) -> None:
        """
        Instantiate the formfield.

        Args:
            stdnum (module): the module of the stdnum library that implements
              validation and formatting of the desired kind of standard number
            args: positional arguments for CharField
            kwargs: keyword arguments for CharField
        """
        self.stdnum = stdnum
        super().__init__(*args, **kwargs)

    def to_python(self, value: str) -> str:
        """Return the compacted python value."""
        value = super().to_python(value)
        return self.stdnum.compact(value)


class ISBNFormField(StdNumFormField):
    """
    Formfield for ISBNFields.

    Converts ISBN-10 input values to ISBN-13.
    """

    def to_python(self, value: str) -> str:
        value = super().to_python(value)
        if value not in self.empty_values and isbn.isbn_type(value) == "ISBN10":
            # Cast the ISBN10 into a ISBN13, so value can match the initial
            # value (which is always ISBN13).
            value = isbn.to_isbn13(value)
        return value


class ISSNFormField(StdNumFormField):
    """
    Formfield for ISSNFields.

    Extracts ISSN from EAN-13 number input values.
    """

    def to_python(self, value: str) -> str:
        value = super().to_python(value)
        if value not in self.empty_values and len(value) == 13:
            # Compacted value is possibly an EAN-13 number.
            # Retrieve the ISSN.
            value = value[3:-3]
            value += issn.calc_check_digit(value)
        return value


class StdNumField(models.CharField):
    """
    The base model field for standard number fields.

    Attributes:
        stdnum: the module of the stdnum library that implements validation and
          formatting of the desired kind of standard number
        min_length (int): minimal length of the number - only used in
          formfield validation
        max_length (int): the maximum length (in characters) of the field
    """

    stdnum = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if self.max_length and "max_length" not in kwargs:
            kwargs["max_length"] = self.max_length
        super().__init__(*args, **kwargs)

    def formfield(self, widget: Optional[forms.TextInput] = None, **kwargs: Any) -> forms.Field:
        defaults = {
            "min_length": self.min_length,
            "stdnum": self.stdnum,
            "form_class": StdNumFormField,
            # Pass this ModelField's validators to the FormField for
            # form-based validation.
            "validators": self.default_validators,
        }
        kwargs = {**defaults, **kwargs}

        # Pass the format callback function to the widget for a
        # prettier display of the value.
        widget_kwargs = {"format_callback": self.get_format_callback()}
        if widget:
            # django-admin will pass its own widget instance to formfield()
            # (or whatever the ModelAdmins.formfield_overrides sets).
            # In order to preserve the prettier output provided by StdNumWidget,
            # overwrite the widget, if that widget is not an instance of
            # StdNumWidget.
            # NOTE: this is a bit oppressive, isn't it?
            if isinstance(widget, type):
                widget_class = widget
            else:
                widget_kwargs["attrs"] = getattr(widget, "attrs", None)  # type: ignore[assignment]
                widget_class = widget.__class__
            if not issubclass(widget_class, StdNumWidget):
                widget_class = StdNumWidget
        else:
            widget_class = StdNumWidget
        kwargs["widget"] = widget_class(**widget_kwargs)  # type: ignore[misc]
        return super().formfield(**kwargs)

    def get_format_callback(self) -> Callable[[str], str]:
        if hasattr(self.stdnum, "format"):
            return self.stdnum.format  # type: ignore[attr-defined]
        # Fallback for ean stdnum which does not have a format function.
        return self.stdnum.compact  # type: ignore[attr-defined]

    def to_python(self, value: str) -> str:
        # In order to deny querying and saving with invalid values, we have to
        # call run_validators.
        # Saving a model instance will not cause the validators to be tested!
        if value not in self.empty_values:
            value = self.stdnum.compact(value)  # type: ignore[attr-defined]
        self.run_validators(value)
        return value


class ISBNField(StdNumField):
    stdnum = isbn
    min_length = 10  # ISBN-10 without dashes/spaces
    max_length = 17  # ISBN-13 with four dashes/spaces
    default_validators = [ISBNValidator]
    description = (
        "Cleaned and validated ISBN string: min length 10 (ISBN-10), max length 17 (13 digits + dashes/spaces)."
    )

    def to_python(self, value: str) -> str:
        # Save the values as ISBN-13.
        if value in self.empty_values:
            return value
        value = super().to_python(value)
        return isbn.to_isbn13(value)

    def get_format_callback(self) -> Callable[[str], str]:
        def _format(value: str) -> str:
            """Return a well formatted ISBN13."""
            if value in self.empty_values:
                return value
            return isbn.format(value, convert=True)

        return _format

    def formfield(self, **kwargs: Any) -> forms.Field:  # type: ignore[override]
        defaults = {"form_class": ISBNFormField}
        return super().formfield(**{**defaults, **kwargs})


class ISSNField(StdNumField):
    stdnum = issn
    min_length = 8  # ISSN without dash/space
    max_length = 9  # ISSN with dash/space
    default_validators = [ISSNValidator]
    description = "Cleaned and validated ISSN string of length 8."

    def formfield(self, **kwargs: Any) -> forms.Field:  # type: ignore[override]
        defaults = {
            # Allow for EAN-13 with dashes/spaces as form data
            "max_length": 17,
            "form_class": ISSNFormField,
        }
        return super().formfield(**{**defaults, **kwargs})


class EANField(StdNumField):
    stdnum = ean  # Note that the ean module does not have a 'format' function
    min_length = 8  # EAN-8
    max_length = 17  # EAN-13 with four dashes/spaces
    default_validators = [EANValidator]
    description = "Cleaned and validated EAN string: min length 8 (EAN-8), max length 17 (13 digits + dashes/spaces)."


"""
PartialDate inspired by:
django-partial-date: https://github.com/ktowen/django_partial_date
https://stackoverflow.com/q/2971198
https://stackoverflow.com/a/30186603
"""


@total_ordering
class PartialDate(datetime.date):
    """
    A datetime.date() that allows constructor arguments to be optional.

    Additional attribute:
        date_format (str): format code (C89 standard) string of the date;
          '%d', '%m' or '%Y', or a combination thereof separated by hyphens '-'
    """

    db_value_template: str = "{year!s:0>4}-{month!s:0>2}-{day!s:0>2}"

    date_format: str = None  # type: ignore[assignment]

    def __new__(cls, year: StrOrInt = None, month: StrOrInt = None, day: StrOrInt = None) -> "PartialDate":
        """
        Create a new PartialDate instance.

        Missing arguments for year, month, day for the date constructor will be
        substituted with minimum values (4 for year, 1 for month/day).
        The original arguments to PartialDate will be stored in the instance
        attributes ``__year``, ``__month``, ``__day``.
        """
        # Default values for the instance's attributes
        instance_attrs: Dict[str, Optional[int]] = {"year": None, "month": None, "day": None}
        # Default values for the datetime.date constructor
        # NOTE: why year: 4?
        constructor_kwargs: Dict[str, int] = {"year": 4, "month": 1, "day": 1}
        date_format = []

        iterator = zip(("year", "month", "day"), (year, month, day), ("%Y", "%m", "%d"))
        for name, value, format_code in iterator:
            if value is None:
                continue
            value = int(value)
            if value != 0:
                constructor_kwargs[name] = value
                instance_attrs[name] = value
                date_format.append(format_code)
        # Call the datetime.date constructor. If the date is invalid,
        # a ValueError will be raised.
        date = super().__new__(cls, **constructor_kwargs)
        # Set the instance's attributes.
        for k, v in instance_attrs.items():
            # The default attrs year,month,day are not writable.
            setattr(date, "__" + k, v)

        date.date_format = "-".join(date_format)
        # noinspection PyTypeChecker
        return date

    @classmethod
    def from_string(cls, date: str) -> "PartialDate":
        """
        Create a PartialDate from the string ``date``.

        Raises:
            ValueError: when the date is not in the format 'YYYY-MM-DD'
        """
        regex = re.compile(r"^(?P<year>\d{4})?(?:-?(?P<month>\d{1,2}))?(?:-(?P<day>\d{1,2}))?$")
        match = regex.match(date)
        if match:
            return cls.__new__(cls, **match.groupdict())
        raise ValueError("Invalid format: 'YYYY-MM-DD' expected.")

    @classmethod
    def from_date(cls, date: datetime.date) -> "PartialDate":
        """Create a PartialDate from a datetime.date() instance."""
        year, month, day, *_ = date.timetuple()
        return cls.__new__(cls, year, month, day)

    @property
    def db_value(self) -> str:
        """Return a string of format 'YYYY-MM-DD' to store in the database."""
        format_kwargs = {"year": 0, "month": 0, "day": 0}
        for attr in ("year", "month", "day"):
            value = getattr(self, "__" + attr, False)
            if value:
                format_kwargs[attr] = value
        return self.db_value_template.format(**format_kwargs)

    def __str__(self) -> str:
        if getattr(self, "__year", None):
            if getattr(self, "__month", None):
                # YYYY-MM or YYYY-MM-DD
                return self.strftime(self.date_format)
            else:
                # We've got a value for year and possibly one for the day;
                # just show the year.
                return str(getattr(self, "__year"))
        else:
            # localized month followed by day (if given) -- or no data at all
            return self.localize()

    def localize(self) -> str:
        """Return a localized date string."""
        if self.date_format:
            # The date is not 'empty'; let django format the date into an
            # alphanumeric, localized form ('01. Mai 2015' or 'Mai 2015').
            # Note that in django, %F is the format code for month localized.
            # Also, the percent signs need to be removed.
            date_format = (
                " ".join(reversed(self.date_format.split("-")))  # date_format is in ISO 8601
                .replace("%d", "%d.")
                .replace("%m", "%F")
                .replace("%", "")
            )
            return formats.date_format(self, date_format)
        return ""

    def __iter__(self) -> Generator:
        """Return the actual values for year, month and day in that order."""
        for attr in ("__year", "__month", "__day"):
            yield getattr(self, attr, None)

    def __len__(self) -> int:
        """Return the length of the string value to be stored in the database."""
        # This allows the MaxLengthValidator of CharField to test the length of
        # the PartialDate.
        return len(self.db_value)

    def __bool__(self) -> bool:
        """Return False if this PartialDate is made of only default values."""
        # Base 'truthiness' of a PartialDate on it having a non-empty
        # date_format. Empty PartialDates thus are recognized as False.
        return bool(self.date_format)

    def __eq__(self, other: Any) -> bool:
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

    def __gt__(self, other: Any) -> bool:
        if isinstance(other, str):
            return self.__str__().__gt__(other)
        return super().__gt__(other)


class PartialDateWidget(forms.MultiWidget):
    """Default widget for the PartialDateFormField."""

    template_name = "partial_date.html"

    def __init__(self, widgets: Optional[Sequence[forms.Widget]] = None, attrs: Optional[dict] = None) -> None:
        if not widgets:
            widgets = []
            for placeholder in ("Jahr", "Monat", "Tag"):
                widgets.append(forms.NumberInput(attrs={"placeholder": placeholder}))
        super().__init__(widgets=widgets, attrs=attrs)

    def get_context(self, name: str, value: Any, attrs: Any) -> dict:
        ctx = super().get_context(name, value, attrs)

        # For django bootstrap to render the error message of an invalid field,
        # the div containing the subwidgets must have the is-invalid class.
        if any(IS_INVALID_CLASS in w["attrs"].get("class", "") for w in ctx["widget"]["subwidgets"]):
            ctx["is_invalid"] = IS_INVALID_CLASS

        # Add required CSS classes.
        # Adding these here because there is some weird stuff going on when
        # declaring the classes in the init or somewhere else; the declared
        # classes seem to prevent the renderer from adding its own classes.
        # The result is that the renderer won't add the is-invalid class to the
        # individual elements if the partial date is invalid.
        for w in ctx["widget"]["subwidgets"]:
            classes = w["attrs"].get("class", "").split(" ")
            classes += ["partial-date", "form-control"]
            w["attrs"]["class"] = " ".join(set(classes)).strip()

        return ctx

    def decompress(self, value: Optional[PartialDate]) -> Union[List[int], List[None]]:
        if isinstance(value, PartialDate):
            return list(value)
        return [None, None, None]

    class Media:
        css = {"all": ["mizdb/css/partialdate.css"]}


class PartialDateFormField(forms.MultiValueField):
    """Default form field for PartialDateField model field."""

    default_error_messages = forms.DateField.default_error_messages

    def __init__(
        self,
        fields: Optional[Sequence[forms.Field]] = None,
        widget: Optional[Type["PartialDateWidget"]] = None,
        **kwargs: Any,
    ) -> None:
        if not fields:
            fields = [forms.IntegerField(required=False)] * 3
        if not widget:
            widget = PartialDateWidget
        elif not (
            (isinstance(widget, type) and issubclass(widget, PartialDateWidget))
            or isinstance(widget, PartialDateWidget)
        ):
            # Replace the given widget if it is not a subclass or instance of
            # PartialDateWidget.
            # (django admin will try to instantiate this formfield with an
            # AdminTextInputWidget)
            # TODO: this should be done via an assertion, raising an error if
            #  the passed in widget is not a PartialDateWidget
            widget = PartialDateWidget

        if "max_length" in kwargs:
            # Remove the max_length kwarg added by CharField.formfield, since
            # that kwarg doesn't apply to MultiValueField.
            del kwargs["max_length"]

        # The point of a PartialDate is that not all attributes of a date need
        # to be set, so require_all_fields should never be True.
        kwargs["require_all_fields"] = False
        super().__init__(fields=fields, widget=widget, **kwargs)

    def compress(self, data_list: List[Union[int, str, None]]) -> PartialDate:
        try:
            return PartialDate(*data_list)
        except ValueError:
            raise ValidationError(self.error_messages["invalid"], code="invalid")


class PartialDateField(models.CharField):
    """
    Model field that handles PartialDate instances.

    Dates are stored as text in ISO 8601 format ('YYYY-MM-DD'). Missing values
    for year, month or day are replaced with zeroes (f.ex. '1969-00-09'). The
    PartialDate constructor will pick up on those zeroes and display the
    partial date accordingly.
    """

    default_error_messages = models.DateField.default_error_messages
    help_text = "Teilweise Angaben sind erlaubt (z.B. Jahr & Monat aber ohne Tag)."

    def __init__(self, *args: Any, null: bool = False, blank: bool = True, help_text: str = "", **kwargs: Any) -> None:
        kwargs["max_length"] = 10  # digits: 4 year, 2 month, 2 day, 2 hyphens
        if not help_text:
            help_text = self.help_text
        super().__init__(*args, null=null, blank=blank, help_text=help_text, **kwargs)

    def to_python(self, value: Union[str, PartialDate, datetime.date, None]) -> PartialDate:
        """Create and return a PartialDate from ``value``."""
        if not value:
            return PartialDate()
        if isinstance(value, str):
            try:
                pd = PartialDate.from_string(value)
            except ValueError:
                # Either from_string could not match its regex or
                # the date produced is invalid (e.g. 02-31)
                raise ValidationError(
                    self.error_messages["invalid_date"],
                    code="invalid_date",
                    params={"value": value},
                )
            return pd
        elif isinstance(value, PartialDate):
            return value
        elif isinstance(value, datetime.date):
            return PartialDate.from_date(value)

    def get_prep_value(self, value: Union[str, PartialDate, datetime.date, None]) -> str:
        """Prepare a value to be stored in the database (object -> db)."""
        value = super().get_prep_value(value)
        return self.to_python(value).db_value

    # noinspection PyMethodMayBeStatic
    def from_db_value(self, value: Optional[str], *_args: Any, **_kwargs: Any) -> Optional[PartialDate]:
        """Create a PartialDate object from a database value (db -> object)."""
        if value is None:
            return value
        return PartialDate.from_string(value)

    def formfield(self, form_class: Optional[Type[forms.Field]] = None, **kwargs: Any) -> forms.Field:
        return super().formfield(form_class=PartialDateFormField, **kwargs)
