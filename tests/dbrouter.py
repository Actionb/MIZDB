# https://docs.djangoproject.com/en/3.2/topics/db/multi-db/#automatic-database-routing

class SQLiteRouter:
    """
    Route dbentry app operations to the default database. Route all other
    operations to the SQLite test database.
    """

    db_name = 'sqlite'

    def db_for_read(self, model, **_hints):
        """
        Suggest the database that should be used for read operations for
        objects of type model.
        """
        # noinspection PyProtectedMember
        if model._meta.app_label == 'dbentry':
            return None
        return self.db_name

    def db_for_write(self, model, **_hints):
        """
        Suggest the database that should be used for writes of objects of type
        Model.
        """
        # noinspection PyProtectedMember
        if model._meta.app_label == 'dbentry':
            return None
        return self.db_name

    # noinspection PyMethodMayBeStatic
    def allow_relation(self, obj1, obj2, **_hints):
        """
        Return True if a relation between obj1 and obj2 should be allowed, False
        if the relation should be prevented, or None if the router has no
        opinion. This is purely a validation operation, used by foreign key and
        many to many operations to determine if a relation should be allowed
        between two objects.
        """
        # noinspection PyProtectedMember
        if obj1._meta.app_label == obj2._meta.app_label:
            return True
        return None  # router test is: if allow is not None

    def allow_migrate(self, db, app_label, **_hints):
        """
        Determine if the migration operation is allowed to run on the database
        with alias db. Return True if the operation should run, False if it
        shouldn’t run, or None if the router has no opinion.

        The app_label positional argument is the label of the application being
        migrated.
        """
        if db == self.db_name:
            print("FOUND ONE")
        return db == self.db_name
        print(f'ROUTER: {db=}, {app_label=}')
        if app_label != 'dbentry':
            return db == self.db_name
        return None  # router test is: if allow is not None
