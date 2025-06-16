#!/usr/bin/env bash

# Drops all test databases (i.e. databases starting with the string "test_mizdb").

echo "This drops the following databases:"
PGPASSWORD="$DB_PASSWORD" psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^("
read -r -p "Continue? [y/n]: "
if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
  echo "Aborted."
  exit 0
fi

PGPASSWORD="$DB_PASSWORD" psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^(" | \
  PGPASSWORD="$DB_PASSWORD" xargs -I {} psql --user=mizdb_user --host=localhost --dbname=mizdb -c "DROP DATABASE {};"
