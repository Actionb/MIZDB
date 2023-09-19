#!/bin/sh
# Restore the database from a backup.
#
# This script first *DELETES* the database and then restores it from a file
# from stdin. The connection parameters are read from the environment.
#
# USAGE:
# 	PGPASSWORD=supersecret POSTGRES_USER=mizdb_user POSTGRES_DB=mizdb ./restore.sh < my_dump
#
# Or for a docker container:
# 	docker exec -i mizdb-postgres /bin/sh -c "PGPASSWORD=supersecret /mizdb/restore.sh" < my_dump

echo "Deleting database..."
dropdb --username="$POSTGRES_USER" --host=localhost "$POSTGRES_DB"
echo "Re-creating database..."
createdb --username="$POSTGRES_USER" --host=localhost --owner="$POSTGRES_USER" "$POSTGRES_DB"
echo "Restoring database data..."
pg_restore --username="$POSTGRES_USER" --host=localhost --dbname "$POSTGRES_DB"
echo "Done!"
