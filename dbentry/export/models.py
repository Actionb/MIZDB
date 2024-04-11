from django.core.exceptions import FieldDoesNotExist
from django.utils.encoding import force_str
from import_export import resources
from import_export.fields import Field

import dbentry.models as _models


class MIZResource(resources.ModelResource):
    _use_overview = True

    def _add_overview(self, queryset):
        """Add 'overview' annotations to the queryset."""
        if self._use_overview and hasattr(queryset, "overview"):
            return queryset.overview()
        else:
            return queryset

    def filter_export(self, queryset, *args, **kwargs):
        return self._add_overview(queryset)

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


class BandResource(MIZResource):
    musiker = Field(column_name="Mitglieder", attribute="musiker_list")
    alias = Field(column_name="Aliase", attribute="alias_list")
    genre = Field(column_name="Genres", attribute="genre_list")
    ort = Field(column_name="Orte", attribute="orte_list")

    class Meta:
        model = _models.Band
        fields = ["id", "band_name", "musiker", "alias", "genre", "ort", "beschreibung"]
        export_order = ["id", "band_name", "musiker", "alias", "genre", "ort", "beschreibung"]
