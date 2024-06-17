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
#   WIKI_URL
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

# URL at which the WIKI is available
WIKI_URL=${WIKI_URL}

# Docker user IDs
UID=$(id -u)
GID=$(id -g)
EOF

# Create a directory for the database data.
mkdir -p db/data

# Create a directory for log files.
mkdir -p logs

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
