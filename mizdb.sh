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
  uninstall     MIZDB deinstallieren

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
  current=$(git rev-parse --abbrev-ref HEAD)
  git remote update
  if [ "$current" != "master" ]; then git checkout master -q; fi
  if docker exec -i $app_container scripts/app/check_update.py; then
    read -r -p "Soll das Update installiert werden? [j/n]: "
    if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
      echo "Abgebrochen."
      if [ "$current" != "master" ]; then git checkout "$current" -q; fi
      exit 1
    fi
    set -e

    # Pull the update:
    git pull -q

    # Rebuild containers:
    echo "Stoppe Container..."
    docker compose down
    echo "Erzeuge Container..."
    docker compose up -d --build
    echo ""

    echo "Führe abschließende Checks aus..."
    docker exec -i $app_container python manage.py check
    echo "Update abgeschlossen!"
    set +e
  fi
  if [ "$current" != "master" ]; then git checkout "$current" -q; fi
}

restart() {
  for container in $app_container $db_container; do
    if [ -n "$(docker container ls -q -f name=$container)" ]; then
      docker restart "$container"
    else
      docker start "$container"
    fi
  done
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
  docker exec -i $app_container python manage.py check
}

collectstatic() {
  docker exec -i $app_container python manage.py collectstatic --clear --no-input --verbosity 0
}

migrate() {
  docker exec -i $app_container python manage.py migrate --no-input
}

uninstall() {
  set -e
  MIZDB_DIR="$(dirname -- "$( readlink -f -- "$0"; )"; )"
  set +a
  source "$MIZDB_DIR/.env"
  set -a

  echo "MIZDB wird deinstalliert."
  echo "WARNUNG: Dabei werden alle Daten gelöscht!"

  read -r -p "Bitte geben Sie 'MIZDB löschen' ein, um zu bestätigen: "
  if [[ ! $REPLY = "MIZDB löschen" ]]; then
    echo "Abgebrochen."
    exit 1
  fi

  echo "Lösche Docker Container..."
  set +e
  docker stop $app_container $db_container
  docker container rm $app_container $db_container
  docker image prune -a
  set -e
  printf "Docker Container gelöscht.\n\n"

  echo "Lösche Datenbankverzeichnis: $(dirname "$DATA_DIR")"
  read -r -p "Fortfahren? [j/N]: "
  if [[ $REPLY =~ ^[jJyY]$ ]]; then
    sudo rm -rf "$(dirname "$DATA_DIR")"
  fi
  echo "Lösche Log Verzeichnis: ${LOG_DIR}"
  read -r -p "Fortfahren? [j/N]: "
  if [[ $REPLY =~ ^[jJyY]$ ]]; then
    sudo rm -rf "$LOG_DIR"
  fi

  echo "Lösche Management Skript."
  sudo rm -f /usr/local/bin/mizdb

  echo "Entferne Backup cronjob."
  # https://askubuntu.com/a/719877
  sudo crontab -l 2>/dev/null | grep -v 'docker exec mizdb-postgres sh /mizdb/backup.sh' | grep -v "Backup der MIZDB Datenbank" | sudo crontab -u root -

  echo "Lösche MIZDB Source Verzeichnis ${MIZDB_DIR}"
  read -r -p "Fortfahren? [j/N]: "
  if [[ ! $REPLY =~ ^[jJyY]$ ]]; then
    exit 1
  fi
  cd ..
  rm -rf "$MIZDB_DIR"
  set +e
  printf "\nFertig!\n"
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
  uninstall) uninstall;;
  *) show_help ;;
esac
