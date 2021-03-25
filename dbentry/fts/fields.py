from django.utils.encoding import force_text

import tsvector_field


class WeightedColumn(tsvector_field.WeightedColumn):
    """
    Extend tsvector_field.WeightedColumn class with a language attribute.

    This allows setting the language of each column of a SearchVectorField.
    The default implementation only allowed one language per SearchVectorField.
    """
    # TODO: add a column language check

    def __init__(self, name, weight, language):
        self.language = language
        super().__init__(name, weight)

    def deconstruct(self):
        """Return a tuple with which the column can be recreated."""
        path = "dbentry.db.base.{}".format(self.__class__.__name__)
        return (
            path,
            [force_text(self.name), force_text(self.weight), force_text(self.language)],
            {}
        )


class SearchVectorField(tsvector_field.SearchVectorField):
    # Adjust SearchVectorField to skip the _check_language_attributes check.

    def _check_language_attributes(self, textual_columns):
        # Skip this check.
        # Changes to WeightedColumn stopped this check from working properly.
        return []

    def deconstruct(self):
        """Return a tuple with which the field can be recreated."""
        # Change the path to so that this SearchVectorField class is used
        # instead of the default implementation:
        name, path, args, kwargs = super().deconstruct()
        return (
            name,
            "dbentry.db.base.{}".format(self.__class__.__name__),
            args,
            kwargs
        )
