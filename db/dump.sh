#!/bin/sh
# Dump the database's data to stdout.
#
# Connection parameters are read from the environment.
#
# USAGE:
# 	PGPASSWORD=supersecret POSTGRES_USER=mizdb_user POSTGRES_DB=mizdb ./dump.sh > dump.db
#
# Or for a docker container:
# 	docker exec -i mizdb-postgres /bin/sh -c "PGPASSWORD=supersecret /mizdb/dump.sh" > dump.db

echo "Creating database backup file..."
pg_dump --username="$POSTGRES_USER" --host=localhost -Fc "$POSTGRES_DB"
echo "Done!"
