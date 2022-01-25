from typing import Any, Dict, Iterator, List, Tuple

import tsvector_field
from django.core import checks
from django.utils.encoding import force_str


class WeightedColumn(tsvector_field.WeightedColumn):
    """
    Extend tsvector_field.WeightedColumn class with a language attribute.

    This allows setting the language (text search config) of each column of a
    SearchVectorField.
    The default implementation only allowed one language per SearchVectorField.
    """

    def __init__(self, name: str, weight: str, language: str) -> None:
        self.language = language
        super().__init__(name, weight)

    def deconstruct(self) -> Tuple[str, list, Dict[str, list]]:
        """
        Return a 3-tuple (path, args, kwargs) with which the column can be
        recreated.
        """
        return (
            "dbentry.fts.fields.{}".format(self.__class__.__name__),
            [force_str(self.name), force_str(self.weight), force_str(self.language)],
            {}
        )


class SearchVectorField(tsvector_field.SearchVectorField):

    def __init__(
            self, blank: bool = True, editable: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        # Set defaults for blank and editable. Note that tsvector_field ALWAYS
        # sets null to True.
        super().__init__(blank=blank, editable=editable, *args, **kwargs)

    def _check_language_attributes(self, textual_columns: List[str]) -> Iterator[checks.Error]:
        """Check that every dbentry.WeightedColumn column has a language set."""
        if self.columns:
            for column in self.columns:
                if isinstance(column, WeightedColumn) and not column.language:
                    yield checks.Error(
                        "Language required for column "
                        f"WeightedColumn({column.name!r}, {column.weight!r}, {column.language!r})",
                        obj=self
                    )

    def deconstruct(self) -> Tuple[str, str, list, Dict[str, list]]:
        """
        Return a 4-tuple (name, path, args, kwargs) with which the field can be
        recreated.
        """
        name, path, args, kwargs = super().deconstruct()
        # The defaults for blank and editable are the exact opposite of those
        # of fields.Field. When Field.deconstruct is called, it will try to
        # omit parameters that have their default value.
        # Obviously, Field.deconstruct checks the parameter values against ITS
        # default values - not against the defaults of SearchVectorField.
        # And since our defaults are the opposite of fields.Field's, that means
        # that Field.deconstruct will omit those parameters when we need
        # to include them, and it will include them when we should omit them.
        if self.blank is not True:
            kwargs['blank'] = False
        else:
            kwargs.pop('blank', None)
        if self.editable is not False:
            kwargs['editable'] = True
        else:
            kwargs.pop('editable', None)
        # Change the path to so that this SearchVectorField class is used
        # instead of the default implementation:
        return (
            name,
            "dbentry.fts.fields.{}".format(self.__class__.__name__),
            args,
            kwargs
        )
