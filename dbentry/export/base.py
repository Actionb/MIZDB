from collections import OrderedDict

from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str
from import_export import widgets
from import_export.fields import Field
from import_export.resources import ModelDeclarativeMetaclass, ModelResource

from dbentry.export.fields import AnnotationField
from dbentry.export.widgets import YesNoBooleanWidget


class MIZDeclarativeMetaclass(ModelDeclarativeMetaclass):
    def __new__(cls, name, bases, attrs):
        # Keep a record of the fields that were declared on this model:
        _declared_fields = OrderedDict()
        for _name, attr in attrs.items():
            if isinstance(attr, Field):
                _declared_fields[_name] = attr

        new_class = super().__new__(cls, name, bases, attrs)

        new_class._meta._declared_fields = _declared_fields

        return new_class


class MIZResource(ModelResource):
    add_annotations = True

    def _add_annotations(self, queryset):
        """Add the annotations declared in `Meta.annotations` to the queryset."""
        if self.add_annotations:
            return queryset.annotate(**self.get_annotations())
        else:
            return queryset

    def filter_export(self, queryset, *args, **kwargs):
        try:
            if queryset.model._meta.get_field("_fts"):
                queryset = queryset.defer("_fts")
        except FieldDoesNotExist:
            pass
        queryset = self._add_annotations(queryset)
        if select_related := getattr(self._meta, "select_related", None):
            queryset = queryset.select_related(*select_related)
        return queryset.order_by(queryset.model._meta.pk.name)

    def get_export_headers(self):
        # For fields derived from the model fields, use the field's
        # verbose_name, unless column_name was set:
        headers = []
        for field in self.get_export_fields():
            try:
                model_field = self._meta.model._meta.get_field(field.attribute)
                verbose_name = model_field.verbose_name.capitalize()
            except FieldDoesNotExist:
                verbose_name = field.column_name
            if field.column_name != field.attribute:
                # Not the default column_name
                headers.append(force_str(field.column_name))
            else:
                headers.append(force_str(verbose_name))
        return headers

    def get_annotations(self):
        """Collect the annotations provided by AnnotationFields."""
        annotations = {}
        for field in self.get_export_fields():
            if isinstance(field, AnnotationField):
                annotations[field.attribute] = field.expr
        return annotations

    @classmethod
    def widget_from_django_field(cls, f, default=widgets.Widget):
        # Override the default for BooleanFields to be a YesNoBooleanWidget:
        boolean_fields = ("BooleanField", "NullBooleanField")
        if callable(getattr(f, "get_internal_type", None)) and f.get_internal_type() in boolean_fields:
            return YesNoBooleanWidget
        return super().widget_from_django_field(f, default)
