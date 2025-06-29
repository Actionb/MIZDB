#!/bin/bash
# Management utility script for the MIZDB app.

if [[ ! $(groups) =~ "docker" ]]; then
  echo "Benutzer '$USER' ist nicht Mitglied der 'docker' Gruppe."
  echo "Führe 'newgrp docker' aus und wiederhole den Befehl."
  echo "https://docs.docker.com/engine/install/linux-postinstall/"
  exit 1
fi

# Names of the docker containers
app_container=mizdb-app
db_container=mizdb-postgres

# Point docker at the env file:
# https://docs.docker.com/compose/how-tos/environment-variables/envvars/#compose_env_files
export COMPOSE_ENV_FILES=${COMPOSE_ENV_FILES:-docker-compose.env}

# Usage info
show_help() {
  cat << EOF
Usage: $0 BEFEHL [BACKUP-DATEI]
Management Programm für die MIZDB app.

BEFEHLE:
  start         MIZDB App Container starten
  stop          MIZDB App Container beenden
  restart       MIZDB App Container neustarten
  reload        Apache Webserver unterbrechungsfrei neustarten (Verbindungen bleiben erhalten)

  restore       Datenbank aus einer Backup-Datei wiederherstellen
  dump          Daten der Datenbank in eine Backup-Datei übertragen

  shell         Kommandozeile des MIZDB App Containers aufrufen
  dbshell       Kommandozeile des Postgresql Containers aufrufen

  check         MIZDB/Django checks ausführen
  update        Nach Updates suchen und installieren
  migrate       Datenbankmigrationen ausführen
  collectstatic Statische Dateien sammeln
  config        Pfad der Konfigurationsdatei anzeigen

EOF
}

dump() {
  file="$1"
  if [ -z "$file" ]; then
    # TODO: read directory for dumps from .env file?
    mkdir -p dumps
    dir=$(readlink -f ./dumps)
    file="$dir/mizdb_$(date +%Y_%m_%d_%H_%M_%S)"
  fi
  echo "Erstelle Datenbank Backup Datei..."
  docker exec -i "$db_container" /bin/sh -c 'pg_dump --username="$POSTGRES_USER" --host=localhost -Fc "$POSTGRES_DB"' > "$file"
  echo "Backup erstellt: $file"
}

restore() {
  if [ -z "$1" ]; then
    echo "Abgebrochen: keine Backup-Datei angegeben: mizdb restore <PFAD_ZUR_BACKUP-DATEI>"
    exit 1
  fi
  echo "Datenbank wird auf den Stand in $1 zurückgesetzt."
  echo "WARNUNG: Die aktuellen Daten werden mit Daten aus $1 überschrieben!"
  read -r -p "Fortfahren? [j/N]: "
  if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
    exit 1
  fi
  # Note that the quotes on 'EOF' make this whole thing work. Why? Magic!
  cmd=$(cat <<'EOF'
echo "Deleting database..." \
&& dropdb --username="$POSTGRES_USER" --host=localhost "$POSTGRES_DB" \
&& echo "Re-creating database..." \
&& createdb --username="$POSTGRES_USER" --host=localhost --owner="$POSTGRES_USER" "$POSTGRES_DB" \
&& echo "Restoring database data..." \
&& pg_restore --username="$POSTGRES_USER" --host=localhost --dbname "$POSTGRES_DB" \
&& echo "Done!"
EOF
  )
  docker exec -i "$db_container" /bin/sh -c "$cmd" < "$1"
}

update() {
  if docker exec -i "$app_container" python manage.py update_available; then
    read -r -p "Soll das Update installiert werden? [j/n]: "
    if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
      echo "Abgebrochen."
      exit 1
    fi
  else
    exit 0
  fi
  set -e

  echo ""
  echo "Lade neueste mizdb.sh herunter..."
  curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/mizdb.sh" -o mizdb.sh
  echo "Lade neuestes Image herunter..."
  docker compose pull
  echo "Starte Container neu..."
  docker compose up -d
  echo ""
  if ! docker exec -i "$app_container" python manage.py migrate --check --no-input; then
    read -r -p "Ausstehende Migrationen anwenden? [j/n]: "
    if [[ $REPLY =~ ^[jJyY]$ ]]; then
      docker exec -i "$app_container" python manage.py migrate --no-input
      echo ""
    else
      echo "Abgebrochen."
      exit 1
    fi
  fi

  echo "Führe abschließende Checks aus..."
  docker exec -i $app_container python manage.py check
  echo "Update abgeschlossen!"
  set +e
}

restart() {
  stop
  start
}

start() {
  docker compose up -d
}

stop() {
  docker compose down
}

reload() {
  docker exec -i $app_container /etc/mizdb-server/apachectl graceful
}

shell() {
  docker exec -it $app_container sh
}

dbshell() {
  docker exec -it $db_container sh
}

check() {
  echo "MIZDB Status:"
  docker exec -i $app_container python manage.py check

  echo ""
  echo "Docker Container Status:"
  docker compose ps
}

collectstatic() {
  docker exec -i $app_container python manage.py collectstatic --clear --no-input --verbosity 0
}

migrate() {
  docker exec -i $app_container python manage.py migrate --no-input
}

config() {
  echo "$PWD"/docker-compose.env
}

case "$1" in
  dump) dump "$2" ;;
  restore) restore "$2" ;;
  update) update ;;
  restart) restart ;;
  start) start ;;
  stop) stop ;;
  reload) reload ;;
  shell) shell ;;
  dbshell) dbshell ;;
  check) check ;;
  collectstatic) collectstatic ;;
  migrate) migrate;;
  config) config;;
  *) show_help ;;
esac
