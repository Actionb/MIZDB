import re
from typing import Any, Iterator, List, Optional, Union


class ItemHandler(object):
    """
    A helper object that extracts values from a string item.

    Intended use is to validate and to extract data from an encoded string
    (i.e. formatted in a specific way) for the dbentry.bulk.fields.SplitField.

    Attributes:
        - ``regex``: either a raw string or a compiled regular expression to
          validate the item with
    """

    regex: Union[str, re.Pattern] = ''

    def __init__(self, regex: Optional[Union[str, re.Pattern]] = None) -> None:
        if regex is not None:
            self.regex = regex
        if isinstance(self.regex, str):
            self.regex = re.compile(self.regex)

    def __call__(self, item: str) -> Iterator[Any]:
        return self.handle(item)

    def handle(self, item: str) -> Iterator[Any]:
        """Extract value(s) from the string item."""
        raise NotImplementedError("Subclasses must implement this method.")

    def is_valid(self, item: str) -> Optional[re.Match]:
        """Validate that this handler can handle the item."""
        return self.regex.search(item)  # type: ignore[union-attr]


class NumericHandler(ItemHandler):
    """ItemHandler for numeric string literals."""

    regex = r'^\d+$'

    def handle(self, item: str) -> Iterator[str]:
        if self.is_valid(item):
            yield item


class RangeHandler(ItemHandler):
    """
    ItemHandler for a range of numeric string literals.

    Expects an item in the form of <start number>-<end number>.

    For example:
        * '1-6' yields  '1', '2', '3', '4', '5', '6'
    """

    regex = r'^(\d+)-(\d+)$'

    def handle(self, item: str) -> Iterator[str]:
        match = self.is_valid(item)
        if match:
            start, end = map(int, match.groups())
            for i in range(start, end + 1):
                yield str(i)


class RangeGroupingHandler(ItemHandler):
    """
    ItemHandler for a range of grouped numeric string literals.

    Expects an item in the form of <start number>-<end number>/<multiplier>.

    For example:
        * '1-6*2' yields ['1', '2'], ['3', '4'], ['5', '6']
        * '1-6*3' yields ['1', '2', '3'], ['4', '5', '6']
    """

    regex = r'^(\d+)-(\d+)\*(\d+)$'

    def handle(self, item: str) -> Iterator[List[str]]:
        match = self.is_valid(item)
        if match:
            start, end, multi = map(int, match.groups())
            for i in range(start, end + 1, multi):
                yield [str(i + j) for j in range(multi)]


class GroupingHandler(ItemHandler):
    """
    ItemHandler for grouped numeric string literals.

    Expects an item in the form of <number1>/<number2>[/...] .

    For example:
        * '1/2/3' yields ['1', '2', '3']
    """

    regex = r'^\d+(/\d+)+$'

    def handle(self, item: str) -> Iterator[List[str]]:
        if self.is_valid(item):
            yield item.split('/')
