#!/usr/bin/env bash

# Drops all test databases (i.e. databases starting with the string "test_mizdb").

# Read password from the password file
PASSWORD=$(cat ".passwd")

echo "This drop the following databases:"
PGPASSWORD="$PASSWORD" psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^("
read -r -p "Continue? [y/n]: "
if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
  echo "Aborted."
  exit 0
fi

PGPASSWORD="$PASSWORD" psql --user=mizdb_user --host=localhost --dbname=mizdb -c "SELECT datname FROM pg_database WHERE datname LIKE 'test_mizdb%';" | \
  grep -ve "datname" -e "^-" -e "^(" | \
  PGPASSWORD="$PASSWORD" xargs -I {} psql --user=mizdb_user --host=localhost --dbname=mizdb -c "DROP DATABASE {};"
