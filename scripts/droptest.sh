#!/usr/bin/env bash

# Drops all test databases (i.e. databases starting with the string "test_mizdb").

set -e

read -r -p 'Database password (leave empty to use default password): '
export PGPASSWORD=${REPLY:-mizdb}

echo "This drops the following databases:"
psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^("
read -r -p "Continue? [y/n]: "
if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
  echo "Aborted."
  exit 0
fi

psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^(" | \
  xargs -I {} psql --user=mizdb_user --host=localhost --dbname=mizdb -c "DROP DATABASE {};"
