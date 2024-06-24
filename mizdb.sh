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
  update        Update MIZDB (git pull)
  restore       Datenbank aus einer Backup-Datei wiederherstellen
  dump          Daten der Datenbank in eine Backup-Datei übertragen
  shell         Kommandozeile des MIZDB App Containers aufrufen
  dbshell       Kommandozeile des Postgresql Containers aufrufen
  check         MIZDB/Django checks ausführen
  migrate       Datenbankmigrationen ausführen
  uninstall     MIZDB deinstallieren
EOF
}

dump() {
  file="$1"
  if [ -z "$file" ]; then
    mkdir -p dumps
    dir=$(readlink -f ./dumps)
    file="$dir/mizdb_$(date +%Y_%m_%d_%H_%M_%S)"
  fi
  echo "Erstelle Datenbank Backup Datei..."
  docker exec -i "$db_container" /bin/sh -c "/mizdb/dump.sh" > "$file"
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
  docker exec -i "$db_container" /bin/sh -c "/mizdb/restore.sh" < "$1"
}

update() {
  git remote update
  # Note that git commands output a lot of information ("chatty feedback") into
  # stderr instead of stdin:
  # https://github.com/git/git/commit/e258eb4800e30da2adbdb2df8d8d8c19d9b443e4
  # This includes the relevant information from `git fetch --dry-run`, so we
  # can't use that command to check whether the local branch can be updated.
  # Use `git rev-list HEAD..@{u}` instead:
  # https://stackoverflow.com/a/20562900/9313033
  if [ -n "$(git rev-list HEAD..@\{u\})" ]; then
    git pull || exit 1
    docker exec -i $app_container pip install --quiet --upgrade -r requirements.txt --root-user-action=ignore
    docker exec -i $app_container python manage.py collectstatic --clear --no-input --verbosity 0
    docker exec -i $app_container python manage.py check
    echo "Updated. Lade den Webserver neu, damit die Änderungen sichtbar werden: mizdb reload"
  else
    echo "Bereits aktuell."
  fi
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

  echo "Lösche MIZDB Source Verzeichnis ${MIZDB_DIR}."
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
