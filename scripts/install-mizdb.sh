#!/usr/bin/env bash
# Installiere MIZDB in den Unterordner 'MIZDB'.

# With some inspiration from the install script for the awesome paperless-ngx project!

set -e

# Run some checks before starting
if [[ $(id -u) == "0" ]] ; then
	echo "Das Skript darf nichts als root ausgeführt werden."
	exit 1
fi

if ! command -v docker &> /dev/null ; then
	echo "docker executable nicht gefunden. Ist docker installiert?"
	exit 1
fi

if ! docker compose &> /dev/null ; then
	echo "docker compose plugin nicht gefunden. Ist docker compose installiert?"
	exit 1
fi

DATA_HOME=${XDG_DATA_HOME:-~/.local/share}
MIZDB_DIR="$DATA_HOME"/MIZDB

echo ""
echo "MIZDB Installation"
echo ""
echo "Dieses Skript wird MIZDB in $MIZDB_DIR installieren."
printf "Fortfahren? (j/n): "
read -r REPLY
if [[ "$REPLY" != [yYjJ]* ]]; then
  echo "Abgebrochen."
  exit 0
fi

# Ask for a password
printf "Soll für den Datenbankbenutzer ein Passwort eingerichtet werden? (j/n): "
read -r REPLY
if [[ "$REPLY" == [yYjJ]* ]]; then
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
fi


# Download the docker files and make configurations on the env file
mkdir -p "$MIZDB_DIR"
cd "$MIZDB_DIR"

echo ""
echo "Lade MIZDB Dateien herunter..."
curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/docker/docker-compose.yaml" -o docker-compose.yaml
curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/docker/docker-compose.env" -o docker-compose.env
curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/mizdb.sh" -o mizdb.sh

echo "Erzeuge MIZDB Einstellungen..."
if [[ $PASSWORD ]]; then sed -i "s/DB_PASSWORD=mizdb/DB_PASSWORD=$PASSWORD/" docker-compose.env; fi
SECRET_KEY=$(LC_ALL=C tr -dc 'a-zA-Z0-9!#%&()*+,-.:;<=>?@[\]^_`{|}~' < /dev/urandom | dd bs=1 count=64 2>/dev/null)
sed -i "s/#SECRET_KEY=/SECRET_KEY=$SECRET_KEY/" docker-compose.env

# Start docker containers
echo ""
echo "Lade Docker Images herunter..."
docker compose --env-file docker-compose.env pull

echo "Starte Docker Container..."
docker compose --env-file docker-compose.env up -d

cd - > /dev/null

# Restore backup or run migrations
restore_cmd=$(cat <<'EOF'
dropdb --username="$POSTGRES_USER" --host=localhost "$POSTGRES_DB" \
&& createdb --username="$POSTGRES_USER" --host=localhost --owner="$POSTGRES_USER" "$POSTGRES_DB" \
&& pg_restore --username="$POSTGRES_USER" --host=localhost --dbname "$POSTGRES_DB"
EOF
)

echo ""
printf "Soll ein Backup wiederhergestellt werden? (j/n): "
read -r REPLY
if [[ "$REPLY" == [yYjJ]* ]]; then
  while true; do
    echo "Bitte Pfad zur Backup-Datei angeben (z.B. ~/Downloads/backup oder ./backup): "
    read -r BACKUP
    BACKUP="$(readlink -f "$BACKUP")"
    if [[ -f "$BACKUP" ]]; then
      break
    else
      echo "Datei nicht gefunden! Bitte benutze absolute (also: /pfad/zu/backup ) oder relative Pfade (also: ./backup )."
    fi
  done
  echo "Stelle Datenbank aus Backup wieder her..."
  docker exec -i mizdb-postgres /bin/sh -c "$restore_cmd" < "$BACKUP"
else
  echo "Wende Datenbank Migration an..."
  docker exec -i mizdb-app python manage.py migrate
fi

set +e

# Add mizdb management utility to the user's path
echo ""
echo "Erstelle Management Skript..."
mkdir -p ~/.local/bin/
cat << EOF > ~/.local/bin/mizdb
#!/bin/sh

file=\$(readlink -f "\$2")
cd $(pwd) || exit
bash mizdb.sh "\$1" "\$file"
cd - > /dev/null || exit
EOF
chmod +x ~/.local/bin/mizdb

echo ""
echo "Fertig!"
echo "Zum Verwalten kann das Management Skript 'mizdb' verwendet werden: mizdb help"
