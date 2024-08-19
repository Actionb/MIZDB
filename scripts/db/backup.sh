#!/bin/sh
# This script manages regular backups of the data of the MIZDB database.
#
# Use this in a cronjob (on the host machine of the docker container):
# > crontab -e
# > 51 7,11,16 * * 1-5  docker exec mizdb-postgres sh /mizdb/backup.sh

BACKUP_DIR="/var/lib/mizdb/backups"
# Numbers of days you want to keep copies of your database:
number_of_days=30

file="${BACKUP_DIR}/mizdb_$(date +%Y_%m_%d_%H_%M_%S)"
pg_dump --username="$POSTGRES_USER" --host=localhost -Fc "$POSTGRES_DB" > "$file"

# Delete older backup copies:
find "$BACKUP_DIR" -name "mizdb_*" -type f -mtime +$number_of_days -delete
