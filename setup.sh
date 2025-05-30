#!/bin/sh
# Create the .secret, and .env file for the docker container.
#
# Parameters read from the environment:
# 	DB_NAME         -- name of the database (defaults to mizdb)
# 	DB_USER         -- user name of the database user (defaults to mizdb_user)
# 	DB_HOST         -- host name of the database container (defaults to db)
# 	DB_PORT         -- port of the database (defaults to 5432)
#   DB_PASSWORD     -- database password (will ask if not set)
#   ALLOWED_HOSTS   -- value for ALLOWED_HOSTS Django setting (will ask if not set)
#   MOUNT_POINT     -- mount point for the apache server (defaults to /miz)
#   DATA_DIR        -- directory for the database data (defaults to /var/lib/mizdb/pgdata)
#   BACKUP_DIR      -- directory for the database backups (defaults to /var/lib/mizdb/backups)
#   LOG_DIR         -- directory for the log files (defaults to /var/log/mizdb)
#
# Prompts for the database password if the environment variable DB_PASSWORD
# is not set.
# Prompts for the hostname if the environment variable ALLOWED_HOSTS is not set.
#
# USAGE:
# 	DB_PASSWORD=supersecret DB_NAME=my_db ALLOWED_HOSTS=example.com sh setup.sh

if [ -n "$DB_PASSWORD" ]; then
  password=$DB_PASSWORD
else
  printf "Please enter database password: "
  read -r password
fi

if [ -n "$ALLOWED_HOSTS" ]; then
  hosts=$ALLOWED_HOSTS
else
  printf "Please enter hostname: "
  read -r hosts
fi

# Create .passwd file for the postgres container (can't use a secrets yaml file)
echo "$password" > .passwd

# Generate the .env file for the Docker container
cat << EOF > .env
# Database connection parameters
DB_NAME=${DB_NAME:-mizdb}
DB_USER=${DB_USER:-mizdb_user}
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}

# The URL path at which the WSGI application will be mounted in the docker container.
# e.g.: MOUNT_POINT=/foo => site available under example.com/foo
MOUNT_POINT=${MOUNT_POINT:-/miz}

# Mounted Directories
DATA_DIR=${DATA_DIR:-/var/lib/mizdb/pgdata}
BACKUP_DIR=${BACKUP_DIR:-/var/lib/mizdb/backups}
LOG_DIR=${LOG_DIR:-/var/log/mizdb}
EOF


# Create a secret key and the secrets file
secret_key=$(python3 -c 'import secrets; allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"; print("".join(secrets.choice(allowed_chars) for _ in range(50)));')

cat << EOF > .secrets
ALLOWED_HOSTS: "$hosts"
DATABASE_PASSWORD: "$password"
SECRET_KEY: "$secret_key"
EOF

# Generate the settings.py file
cat << EOF > settings.py
"""
Add your own settings that override the default settings.

For a list of settings, see:
    - https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from MIZDB.settings.production import *  # noqa

# -----------------------------------------------------------------------------
# Add your own settings here:

EOF
