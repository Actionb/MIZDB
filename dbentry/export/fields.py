from functools import cached_property

from import_export.fields import Field


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

    def export(self, obj):
        try:
            return self.cache[obj.pk][self.attribute]
        except KeyError:
            return ""
