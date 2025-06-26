from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str
from import_export import widgets
from import_export.resources import ModelResource

from dbentry.export.fields import AnnotationField
from dbentry.export.widgets import YesNoBooleanWidget


class MIZResource(ModelResource):
    add_annotations = True

    def _add_annotations(self, queryset):
        """Add the annotations declared in `Meta.annotations` to the queryset."""
        if self.add_annotations:
            return queryset.annotate(**self.get_annotations())
        else:
            return queryset

    def _defer_fts(self, queryset):
        """Defer the ``_fts`` (text search) field from the queryset."""
        try:
            if queryset.model._meta.get_field("_fts"):
                queryset = queryset.defer("_fts")
        except FieldDoesNotExist:
            pass
        return queryset

    def _select_related(self, queryset):
        """Add select_related to the given queryset."""
        if select_related := getattr(self._meta, "select_related", None):
            queryset = queryset.select_related(*select_related)
        return queryset

    def filter_export(self, queryset, *args, **kwargs):
        queryset = self._defer_fts(self._add_annotations(self._select_related(queryset)))
        return queryset.order_by(queryset.model._meta.pk.name)

    def get_export_headers(self, selected_fields=None):
        # For fields derived from the model fields, use the field's
        # verbose_name, unless column_name was set:
        headers = []
        for field in self.get_export_fields(selected_fields):
            try:
                model_field = self._meta.model._meta.get_field(field.attribute)
                if model_field.verbose_name == model_field.name.replace("_", " "):
                    # The verbose name was derived from the field name; ensure
                    # that the first letter is upper case. Do not use
                    # str.capitalize here because some fields like "ISBN" are
                    # supposed to be all upper case, which capitalize() would
                    # turn into "Isbn".
                    verbose_name = f"{model_field.verbose_name[0].upper()}{model_field.verbose_name[1:]}"
                else:
                    # An explicit verbose name was set. Assume that the
                    # capitalization is appropriate here.
                    verbose_name = model_field.verbose_name
            except FieldDoesNotExist:
                verbose_name = field.column_name
            if field.column_name is not None and field.column_name != field.attribute:
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
