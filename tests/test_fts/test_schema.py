from unittest.mock import Mock, patch

from django.db import connection
from django.test import TestCase

from dbentry.fts.db.schema import MIZDBSchemaEditor, MIZDBTriggerEditor
from dbentry.fts.fields import WeightedColumn


class TestMIZDBTriggerEditor(TestCase):
    def test_sql_setweight(self):
        """Assert that setweight uses the language defined in the column declaration."""
        field = Mock(
            columns=[
                WeightedColumn("title", "A", language="simple"),
                WeightedColumn("body", "D", language="german"),
            ]
        )

        with MIZDBSchemaEditor(connection) as schema_editor:
            sql = MIZDBTriggerEditor(schema_editor)._to_tsvector_weights(field)

        expected = [
            """ setweight(to_tsvector('simple', COALESCE(NEW."title", '')), 'A') ||""",
            """ setweight(to_tsvector('german', COALESCE(NEW."body", '')), 'D');""",
        ]
        self.assertEqual(sql, expected)


class TestMIZDBSchemaEditor(TestCase):
    def test_trigger_editor_class(self):
        """
        Assert that MIZDBSchemaEditor passes the editor calls and arguments
        on to the trigger editor given by the trigger_editor_class attribute.
        """
        mocked_create = Mock()
        mocked_delete = Mock()
        mocked_add = Mock()
        mocked_remove = Mock()
        mocked_alter = Mock()
        mocked_trigger_editor_class = Mock(
            return_value=Mock(
                create_model=mocked_create,
                delete_model=mocked_delete,
                add_field=mocked_add,
                remove_field=mocked_remove,
                alter_field=mocked_alter,
            )
        )
        with patch("dbentry.fts.db.schema.super"):
            schema_editor = MIZDBSchemaEditor(connection)
            with patch.object(schema_editor, "trigger_editor_class", mocked_trigger_editor_class):
                schema_editor.create_model("model")
                mocked_create.assert_called_with("model")
                schema_editor.delete_model("model")
                mocked_delete.assert_called_with("model")
                schema_editor.add_field("model", "field")
                mocked_add.assert_called_with("model", "field")
                schema_editor.remove_field("model", "field")
                mocked_remove.assert_called_with("model", "field")
                schema_editor.alter_field("model", "old_field", "new_field", strict=True)
                mocked_alter.assert_called_with("model", "old_field", "new_field")
