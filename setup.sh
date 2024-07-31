#!/bin/sh
# Create secret files, an .env file and directories for the docker container.
#
# Parameters read from the environment:
# 	DB_NAME
# 	DB_USER
# 	DB_HOST
# 	DB_PORT
#   DB_PASSWORD
#   ALLOWED_HOSTS
#   MOUNT_POINT
#
# Prompts for the database password if the environment variable DB_PASSWORD
# is not set.
# Prompts for the hostname if the environment variable ALLOWED_HOSTS is not set.
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

# Docker user IDs
UID=$(id -u)
GID=$(id -g)
EOF

# Create a directory for the database data.
mkdir -p db/data

# Create a directory for log files.
mkdir -p logs

# Create the secrets file.
if [ -n "$DB_PASSWORD" ]; then
  password=$DB_PASSWORD
else
  printf "Please enter database password: "
  read -r password
fi
# Create .passwd file for the postgres container (can't use a secrets yaml file)
echo "$password" > .passwd

if [ -n "$ALLOWED_HOSTS" ]; then
  hosts=$ALLOWED_HOSTS
else
  printf "Please enter hostname: "
  read -r hosts
fi

secret_key=$(python3 -c 'import secrets; allowed_chars = "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)"; print("".join(secrets.choice(allowed_chars) for _ in range(50)));')

cat << EOF > .secrets
ALLOWED_HOSTS: $hosts
DATABASE_PASSWORD: $password
SECRET_KEY: $secret_key
EOF
