#!/bin/sh
# Create secret files and the .env file for the docker container.
#
# Parameters read from the environment:
# 	DB_NAME         -- name of the database (defaults to mizdb)
# 	DB_USER         -- user name of the database user (defaults to mizdb_user)
# 	DB_HOST         -- host name of the database container (defaults to db)
# 	DB_PORT         -- port of the database (defaults to 5432)
#   DB_PASSWORD     -- database password (will ask if not set)
#   ALLOWED_HOSTS   -- value for ALLOWED_HOSTS Django setting (will ask if not set)
#   WIKI_URL        -- URL to the MIZDB WIKI
#   MOUNT_POINT     -- mount point for the apache server (defaults to /miz)
#   DATA_DIR        -- directory for the database data (defaults to /var/lib/mizdb/pgdata)
#   LOG_DIR         -- directory for the log files (defaults to /var/log/mizdb)
#
# USAGE:
# 	DB_PASSWORD=supersecret DB_NAME=my_db ALLOWED_HOSTS=example.com sh setup.sh

cat << EOF > .env
# Database connection parameters
DB_NAME=${DB_NAME:-mizdb}
DB_USER=${DB_USER:-mizdb_user}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

# The URL path at which the WSGI application will be mounted in the docker container.
# e.g.: MOUNT_POINT=/foo => site available under example.com/foo
MOUNT_POINT=${MOUNT_POINT:-/miz}

# URL at which the WIKI is available
WIKI_URL=${WIKI_URL}

# Mounted Directories
DATA_DIR=${DATA_DIR:-/var/lib/mizdb/pgdata}
LOG_DIR=${LOG_DIR:-/var/log/mizdb}
EOF

# Create the secrets directory and secret files.
mkdir -p .secrets
python3 -c 'import secrets; allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"; print("".join(secrets.choice(allowed_chars) for _ in range(50)));' > .secrets/.key

if [ -n "$DB_PASSWORD" ]; then
  password=$DB_PASSWORD
else
  printf "Please enter database password: "
  read -r password
fi
echo "$password" > .secrets/.passwd

if [ -n "$ALLOWED_HOSTS" ]; then
  hosts=$ALLOWED_HOSTS
else
  printf "Please enter hostname: "
  read -r hosts
fi
echo "$hosts" > .secrets/.allowedhosts
