#!/bin/sh
# Dieses Skript wird zunächst systemweit Docker und dann MIZDB in den
# Unterordner 'MIZDB' installieren.
# Es kann eine Datei mit den Daten der Datenbank an das Skript übergeben
# werden und das Skript wird diese Daten in die neue Installation einlesen.
#
# BENUTZUNG:
# 	sh get-mizdb.sh db_backup_datei
# oder mit vordefiniertem Passwort und Hostnamen:
# 	$DB_PASSWORD=passwort ALLOWED_HOSTS=hostname sh get-mizdb.sh db_backup_datei

set -e

if [ -n "$DB_PASSWORD" ]; then
  password=$DB_PASSWORD
else
  printf "Bitte Passwort für die Datenbank eingeben: "
  read -r password
fi

if [ -n "$ALLOWED_HOSTS" ]; then
  hosts=$ALLOWED_HOSTS
else
  printf "Bitte Hostnamen eingeben: "
  read -r hosts
fi

install_docker() {
  # Install Docker using their 'convenience' script
  # https://docs.docker.com/engine/install/debian/#install-using-the-convenience-script
  printf "\nInstalliere Docker...\n\n"
  if command -v "docker" > /dev/null 2>&1; then
    printf "Docker scheint bereits installiert zu sein. Trotzdem installieren (y/n)?: "
    read -r REPLY
    case "$REPLY" in
      [!JjYy]*) return 0 ;;
    esac
  fi

  sudo apt update -qq && sudo apt install -y -qq curl
  curl -fsSL https://get.docker.com -o get-docker.sh
  sh get-docker.sh
  rm -f get-docker.sh
  printf "\nDocker erfolgreich installiert!\n"

  # Linux post-install
  # https://docs.docker.com/engine/install/linux-postinstall/
  set +e
  printf "\nRichte docker ein...\n\n"

  # Run docker as non-root
  sudo groupadd docker
  sudo usermod -aG docker "$USER"

  # Start docker services on boot
  sudo systemctl enable docker.service
  sudo systemctl enable containerd.service

  printf "\nDocker erfolgreich eingerichtet!\n"
  set -e
}

setup_mizdb() {
  if [ -d "MIZDB" ]; then
    printf "MIZDB scheint bereits installiert zu sein. Trotzdem fortfahren (y/n)?: "
    read -r REPLY
    case "$REPLY" in
      [!JjYy]*) return 0 ;;
    esac
  fi
  printf "\nLade MIZDB herunter...\n\n"
  mkdir -p MIZDB
  sudo apt install -y -qq git
  git clone https://github.com/Actionb/MIZDB MIZDB
  cd MIZDB
  DB_PASSWORD=$password ALLOWED_HOSTS=$hosts /bin/sh setup.sh
  printf "\nErzeuge Docker Container...\n\n"
  sudo docker compose up -d
  printf "\nContainer erstellt!\n\n"
  restored=false
  if [ -f "$1" ]; then
    set +e
	if sudo docker exec -i mizdb-postgres /bin/sh -c "/mizdb/restore.sh" < "$1"; then
      restored=true
	fi
	set -e
  fi
  echo "Erstelle Management Skript..."
  cat << EOF | sudo tee /usr/local/bin/mizdb > /dev/null
#!/bin/sh

file=\$(readlink -f "\$2")
cd $(pwd) || exit
bash mizdb.sh "\$1" "\$file"
cd - > /dev/null || exit
EOF
  sudo chmod +x /usr/local/bin/mizdb

  cd - > /dev/null
  if [ "$restored" = false ]; then
	cat <<- EOF

	  Achtung:

	    Datenbank nicht eingerichtet.

	    Falls eine Backup-Datei vorhanden ist, so kann die Datenbank mit dem
	    folgenden Befehl wiederhergestellt werden:
	        mizdb restore <backup_datei>

	    Oder führe die Datenbank-Migrationen der App aus:
	        mizdb shell
	        python manage.py migrate

EOF
  fi
  printf "\nInstallation erfolgreich!\n"
  echo "Datenbank-Seite ist erreichbar unter: http://$hosts/miz/"
  echo "Benutze den 'mizdb' Befehl, um die App zu verwalten."
}

install_docker
setup_mizdb "$(readlink -f "$1")"
