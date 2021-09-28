from django.db.backends.postgresql.schema import DatabaseSchemaEditor as PostgreSQLSchemaEditor
from tsvector_field.schema import DatabaseTriggerEditor


class MIZDBTriggerEditor(DatabaseTriggerEditor):
    """
    Extend DatabaseTriggerEditor to account for the column.language attribute.
    """

    def _to_tsvector_weights(self, field):
        sql_setweight = (
            " setweight(to_tsvector({language}, COALESCE(NEW.{column}, '')), {weight}) ||"
        )

        weights = []
        for column in field.columns:
            weights.append(sql_setweight.format(
                # FIXME: catch invalid column.language (f.ex. empty string)
                language=self.quote_value(column.language),
                column=self.quote_name(column.name),
                weight=self.quote_value(column.weight)
            ))
        weights[-1] = weights[-1][:-3] + ';'

        return weights


class MIZDBSchemaEditor(PostgreSQLSchemaEditor):
    """
    Schema editor class with a trigger_editor_class attribute.

    tsvector_field's schema editor calls the trigger editor class directly in
    each method, i.e.:
        DatabaseTriggerEditor(self).create_model(model)
    Changing the trigger editor class thus means that each method must be
    changed. To facilitate custom editors, introduce a trigger_editor_class
    attribute that is then called instead.
    """

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
