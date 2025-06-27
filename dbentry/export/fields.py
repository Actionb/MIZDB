from functools import cached_property

from import_export.fields import Field

from dbentry.export.widgets import ChoiceLabelWidget


class AnnotationField(Field):
    """A Resource Field with an annotation expression for the export queryset."""

    def __init__(self, *args, expr=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.expr = expr


class CachedQuerysetField(Field):
    """A Resource Field that returns its export value from a cached queryset."""

    def __init__(self, *args, queryset=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryset = queryset

    @cached_property
    def cache(self):
        cache = {}
        pk_name = self.queryset.model._meta.pk.name
        for values_dict in self.queryset.values(pk_name, self.attribute):
            pk = values_dict.pop(pk_name)
            cache[pk] = values_dict
        return cache

    def export(self, instance, **kwargs):
        try:
            return self.cache[instance.pk][self.attribute]
        except KeyError:
            return ""


class ChoiceField(Field):
    """
    A Resource Field for fields with choices that exports the human-readable
    label of the selected choice.
    """

    def __init__(self, attribute=None, widget=None, **kwargs):
        if widget is None and attribute is not None:
            widget = ChoiceLabelWidget(field_name=attribute)
        super().__init__(attribute=attribute, widget=widget, **kwargs)
