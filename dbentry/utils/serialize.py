from collections import OrderedDict
from typing import Generator

from django.core.serializers.python import Serializer as BaseSerializer
from django.utils.text import capfirst


class RelatedStringSerializer(BaseSerializer):
    """
    A python serializer that uses string representation for related objects
    (instead of primary key values).
    """

    def handle_fk_field(self, obj, field):
        """Return a string representation of the related object."""
        self._current[field.name] = str(getattr(obj, field.name))

    def handle_m2m_field(self, obj, field):
        """
        Return a comma-separated list of string representations of the related
        objects.
        """
        m2m_iter = getattr(obj, '_prefetched_objects_cache', {}).get(
            field.name,
            getattr(obj, field.name).iterator(),
        )
        self._current[field.name] = ", ".join([str(related) for related in m2m_iter])


def _get_label(field):
    if field.many_to_many:
        return field.related_model._meta.verbose_name_plural
    return capfirst(field.verbose_name or field.name.replace('_', ' '))


def get_documents(queryset, fields=None, remove_empty=True, hooks=None) -> Generator[OrderedDict]:
    """
    Yield ordered value dictionaries for the objects in ``queryset``.

    Args:
        queryset: the queryset of objects to get the values of
        fields: the field names/paths to include
        remove_empty: if True, do not include 'empty' values
        hooks: a mapping of a field name from ``fields`` and a callable that
          returns a (label, value) pair for the current row
    """
    for row in RelatedStringSerializer().serialize(queryset, fields=fields):
        document = OrderedDict()
        document['Objekt'] = queryset.model._meta.verbose_name
        document['ID'] = row['pk']
        ordering = fields or sorted(row['fields'].keys())
        for field_name in ordering:
            try:
                value = row['fields'][field_name]
            except KeyError:
                # This model has no (local) field with that name (the serializer
                # would have included the field otherwise). Check if the caller
                # wants to inject extra data here via a hook.
                # NOTE: could insert extra data here; like values of fields not
                #  directly related to the model (f.ex. magazin for artikel.ausgabe)
                # TODO: we should do this in the serializer, so we can call the
                #  hook with the model instance, instead of with just the pk
                if hooks and field_name in hooks:
                    label, value = hooks[field_name](row)
                    document[label] = value
                continue
            field = queryset.model._meta.get_field(field_name)
            if remove_empty and value in (*field.empty_values, field.default):
                # TODO: only remove empty values if remove_empty - for removing
                #  default values, use another parameter
                continue
            document[_get_label(field)] = value
        yield document
