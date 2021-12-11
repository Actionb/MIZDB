# This wrapper allows the database engine to make use of the SearchVectorField.
from django.db.backends.postgresql import base

from dbentry.fts.db.schema import MIZDBSchemaEditor


class DatabaseWrapper(base.DatabaseWrapper):
    SchemaEditorClass = MIZDBSchemaEditor
