import re
from typing import Any, Dict, Optional, Sequence, Tuple

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import Widget

from dbentry.tools.bulk.handlers import (
    GroupingHandler, NumericHandler, RangeGroupingHandler, RangeHandler
)


class BaseSplitField(forms.CharField):
    """
    A CharField that splits its data into a sequence of values.

    The field's data is split into a sequence of values via a regular
    expression. A series of handlers are run on these values to determine the
    validity of each value.
    The field's ``to_list`` method will apply the handlers to each value again
    to produce the sequence of final results.

    Example, with a simple NumericHandler for the individual values:
        data: '1,2,3,4' -> result sequence: ['1', '2', '3', '4']

    Example, with a RangeHandler:
        data: '2-5' -> result sequence: ['2', '3', '4', '5']

    Attributes:
        - ``separator_pattern`` (str): pattern for a regular expression to
          split the field's data with.
        - ``item_handlers``: a sequence of Handler instances that validate each
          item in the field's data and extract the final values from the item.
          Validation for an item stops once a handler deemed it valid, thus the
          order of the handlers can matter if their regexes are similar.
    """

    separator_pattern: str = r','
    item_handlers: Sequence = ()
    default_error_messages: Dict[str, str] = {'invalid': 'Ungültige Angabe(n): %(invalid)s.'}

    def __init__(
            self,
            separator_pattern: Optional[str] = None,
            item_handlers: Optional[Sequence] = None,
            *args: Any,
            **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if separator_pattern is not None:  # pragma: no cover
            self.separator_pattern = separator_pattern
        if item_handlers is not None:  # pragma: no cover
            self.item_handlers = item_handlers
        self.separator_regex = re.compile(self.separator_pattern)

    def validate(self, value: str) -> None:
        """Run validation on each item of value using the field's handlers."""
        super().validate(value)
        if not value:
            return
        invalid = []
        for item in self.separator_regex.split(value):
            if not any(h.is_valid(item) for h in self.item_handlers):
                invalid.append(item)
        if invalid:
            raise ValidationError(
                self.error_messages['invalid'],
                code='invalid',
                params={'invalid': ", ".join(invalid)}
            )

    def clean(self, value: str) -> str:
        if value:
            # Remove whitespaces and empty items.
            value = self.separator_pattern.join(
                [
                    item.replace(' ', '')
                    for item in self.separator_regex.split(value)
                    if item.strip()
                ]
            )
        return super().clean(value)

    def widget_attrs(self, widget: Widget) -> dict:
        attrs = super().widget_attrs(widget)
        # Limit the width of the SplitField's widget to 350px.
        attrs['style'] = 'width:350px;'
        return attrs

    def to_list(self, value: str) -> Tuple[list, int]:
        """
        Run handlers on each item of value.

        Return a list of the results and the length of that list.
        """
        if not value:
            return [], 0

        result = []
        for item in self.separator_regex.split(value):
            for handler in self.item_handlers:
                if handler.is_valid(item):
                    result.extend(handler(item))
                    break
        return result, len(result)


class BulkField(BaseSplitField):
    """The default formfield for the BulkForm."""

    item_handlers: Sequence = (
        RangeGroupingHandler(), RangeHandler(), GroupingHandler(), NumericHandler()
    )

    def __init__(self, required: bool = False, *args: Any, **kwargs: Any) -> None:
        super().__init__(required=required, *args, **kwargs)


class BulkJahrField(BaseSplitField):
    """A SplitField that only accepts numerical values with 4 digits."""

    item_handlers: Sequence = (NumericHandler(),)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Add a validator that only allows numerals with 4 digits or the
        # separator.
        self.validators.append(
            RegexValidator(
                regex=r'^(\d{4}|%s)*$' % self.separator_pattern,
                message='Bitte vierstellige Jahresangaben benutzen.',
                code='invalid_year'
            )
        )
