# This wrapper is required for the django-tsvector-field app to work properly.
from django.db.backends.postgresql import base
from django.utils.encoding import force_text
from tsvector_field.schema import DatabaseTriggerEditor
from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgreSQLSchemaEditor
import tsvector_field


class WeightedColumn(tsvector_field.WeightedColumn):

    def __init__(self, name, weight, language):
        self.language = language
        super().__init__(name, weight)

    def deconstruct(self):
        path = "dbentry.db.base.{}".format(self.__class__.__name__)
        return path, [force_text(self.name), force_text(self.weight), force_text(self.language)], {}


class SearchVectorField(tsvector_field.SearchVectorField):

    def _check_language_attributes(self, textual_columns):
        # Check implementation doesn't work with per column language.
        return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        return name, "dbentry.db.base.{}".format(self.__class__.__name__), args, kwargs


class MIZDBTriggerEditor(DatabaseTriggerEditor):

    def _to_tsvector_weights(self, field):
        sql_setweight = (
            " setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"
        )

        weights = []
        for column in field.columns:
            weights.append(sql_setweight.format(
                language=self.quote_value(column.language),
                column=self.quote_name(column.name),
                weight=self.quote_value(column.weight)
            ))
        weights[-1] = weights[-1][:-3] + ';'

        return weights


class MIZDBSchemaEditor(PostgreSQLSchemaEditor):
    trigger_editor_class = MIZDBTriggerEditor

    def create_model(self, model):
        super().create_model(model)
        self.trigger_editor_class(self).create_model(model)

    def delete_model(self, model):
        super().delete_model(model)
        self.trigger_editor_class(self).delete_model(model)

    def add_field(self, model, field):
        super().add_field(model, field)
        self.trigger_editor_class(self).add_field(model, field)

    def remove_field(self, model, field):
        super().remove_field(model, field)
        self.trigger_editor_class(self).remove_field(model, field)

    def alter_field(self, model, old_field, new_field, strict=False):
        super().alter_field(model, old_field, new_field)
        self.trigger_editor_class(self).alter_field(model, old_field, new_field)


class DatabaseWrapper(base.DatabaseWrapper):
    SchemaEditorClass = MIZDBSchemaEditor
