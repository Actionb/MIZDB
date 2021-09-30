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
        """
        Return a 3-tuple (path, args, kwargs) with which the column can be
        recreated.
        """
        return (
            "dbentry.fts.fields.{}".format(self.__class__.__name__),
            [force_text(self.name), force_text(self.weight), force_text(self.language)],
            {}
        )


class SearchVectorField(tsvector_field.SearchVectorField):
    # Adjust SearchVectorField to skip the _check_language_attributes check.
    
    def __init__(self, blank=True, editable=False, *args, **kwargs):
        # Set defaults for blank and editable. Note that tsvector_field ALWAYS
        # sets null to True.
        super().__init__(blank=blank, editable=editable, *args, **kwargs)

    def _check_language_attributes(self, textual_columns):
        # Skip this check.
        # Changes to WeightedColumn stopped this check from working properly.
        return []

    def deconstruct(self):
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
        # to include them and it will include them when we should omit them.
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
