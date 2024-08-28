from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgreSQLSchemaEditor
from tsvector_field.schema import DatabaseTriggerEditor


class MIZDBTriggerEditor(DatabaseTriggerEditor):
    """
    Extend tsvector_field.DatabaseTriggerEditor to include the language
    attribute of a column.

    SearchVectorField attributes 'language' and 'language_column' will be
    ignored when creating the setweight SQL.
    """

    def _to_tsvector_weights(self, field):  # type: ignore[no-untyped-def]
        sql_setweight = " setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"

        weights = []
        for column in field.columns:
            weights.append(
                sql_setweight.format(
                    language=self.quote_value(column.language),
                    column=self.quote_name(column.name),
                    weight=self.quote_value(column.weight),
                )
            )
        weights[-1] = weights[-1][:-3] + ";"

        return weights


class MIZDBSchemaEditor(PostgreSQLSchemaEditor):
    """
    Schema editor that calls another 'trigger' editor that extends the editor
    SQL with triggers for the search vector fields.
    """

    trigger_editor_class = MIZDBTriggerEditor

    def create_model(self, model):  # type: ignore[no-untyped-def]
        super().create_model(model)
        self.trigger_editor_class(self).create_model(model)

    def delete_model(self, model):  # type: ignore[no-untyped-def]
        super().delete_model(model)
        self.trigger_editor_class(self).delete_model(model)

    def add_field(self, model, field):  # type: ignore[no-untyped-def]
        super().add_field(model, field)
        self.trigger_editor_class(self).add_field(model, field)

    def remove_field(self, model, field):  # type: ignore[no-untyped-def]
        super().remove_field(model, field)
        self.trigger_editor_class(self).remove_field(model, field)

    def alter_field(self, model, old_field, new_field, strict=False):  # type: ignore[no-untyped-def]
        super().alter_field(model, old_field, new_field)
        self.trigger_editor_class(self).alter_field(model, old_field, new_field)
