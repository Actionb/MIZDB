#!/bin/sh
# This script manages regular backups of the data of the MIZDB database.
#
# Use this in a cronjob (on the host machine of the docker container):
# > crontab -e
# > 51 7,11,16 * * 1-5  /path/to/this/backup.sh

# The directory where the backups should go:
BACKUP_DIR="/var/lib/mizdb/backups"
# The name of the db container:
db_container=mizdb-postgres
# Numbers of days you want to keep copies of the database dumps:
number_of_days=30

file="${BACKUP_DIR}/mizdb_$(date +%Y_%m_%d_%H_%M_%S)"
docker exec -i "$db_container" /bin/sh -c 'pg_dump --username="$POSTGRES_USER" --host=localhost -Fc "$POSTGRES_DB"' > "$file"

# Delete older backup copies:
find "$BACKUP_DIR" -name "mizdb_*" -type f -mtime +$number_of_days -delete
