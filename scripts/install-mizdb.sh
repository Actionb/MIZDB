#!/usr/bin/env bash
# Install MIZDB.
#
# Inspired by the install script from the awesome paperless-ngx project!

set -e

if [[ $(id -u) == "0" ]] ; then
	echo "Do not run this script as root."
	exit 1
fi

if ! command -v wget &> /dev/null ; then
	echo "wget executable not found. Is wget installed?"
	exit 1
fi

if ! command -v docker &> /dev/null ; then
	echo "docker executable not found. Is docker installed?"
	exit 1
fi

if ! docker compose &> /dev/null ; then
	echo "docker compose plugin not found. Is docker compose installed?"
	exit 1
fi

ask_pw () {
  printf "Soll für den Datenbankbenutzer ein Passwort eingerichtet werden (y/n)?: "
  read -r REPLY
  case "$REPLY" in
    [!JjYy]*) return 0 ;;
  esac
  while true; do
    read -r -sp "Bitte Passwort für den Datenbankbenutzer eingeben: " PASSWORD
    echo ""

    if [[ -z $PASSWORD ]] ; then
      echo "Passwort darf nicht leer sein."
      continue
    fi

    read -r -sp "Bitte das Passwort noch einmal eingeben: " PASSWORD_REPEAT
    echo ""

    if [[ ! "$PASSWORD" == "$PASSWORD_REPEAT" ]] ; then
      echo "Passwörter stimmen nicht überein"
    else
      break
    fi
  done
}

ask_pw

# TODO: ask for an install folder?
mkdir -p MIZDB
cd MIZDB

echo "Lade MIZDB Dateien herunter..."
# TODO: set correct URLs
wget "https://raw.githubusercontent.com/Actionb/MIZDB/refs/heads/feature/docker-image/docker/docker-compose.yaml" -q -O docker-compose.yaml
wget "https://raw.githubusercontent.com/Actionb/MIZDB/refs/heads/feature/docker-image/docker/docker-compose.env" -q -O docker-compose.env
wget "https://raw.githubusercontent.com/Actionb/MIZDB/refs/heads/feature/docker-image/mizdb.sh" -q -O mizdb.sh

echo "Erzeuge MIZDB Einstellungen..."
if [[ $PASSWORD ]]; then sed -i "s/DB_PASSWORD=mizdb/DB_PASSWORD=$PASSWORD/" docker-compose.env; fi
SECRET_KEY=$(LC_ALL=C tr -dc 'a-zA-Z0-9!#$%&()*+,-.:;<=>?@[\]^_`{|}~' < /dev/urandom | dd bs=1 count=64 2>/dev/null)
sed -i "s/#SECRET_KEY=/SECRET_KEY=$SECRET_KEY/" docker-compose.env

echo "Lade Docker Images herunter..."
docker compose --env-file docker-compose.env pull

echo "Starte Docker Container..."
docker compose --env-file docker-compose.env up -d

echo "Erstelle Management Skript..."
cat << EOF > ~/.local/bin/mizdb
#!/bin/sh

file=\$(readlink -f "\$2")
cd $(pwd) || exit
bash mizdb.sh "\$1" "\$file"
cd - > /dev/null || exit
EOF
chmod +x ~/.local/bin/mizdb

if [ -f "$1" ]; then
  echo "Stelle Datenbank aus Backup wieder her..."
  cmd=$(cat <<'EOF'
dropdb --username="$POSTGRES_USER" --host=localhost "$POSTGRES_DB" \
&& createdb --username="$POSTGRES_USER" --host=localhost --owner="$POSTGRES_USER" "$POSTGRES_DB" \
&& pg_restore --username="$POSTGRES_USER" --host=localhost --dbname "$POSTGRES_DB"
EOF
  )
  docker exec -i mizdb-postgres /bin/sh -c "$cmd" < "$1"
else
  echo "Erzeuge Datenbank Tabellen..."
  docker exec -i mizdb-app python manage.py migrate
fi

echo "Fertig!"
