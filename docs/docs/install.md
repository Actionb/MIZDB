Installation Debian (Docker)
=======

## Per script

Das Script installiert Docker und lädt MIZDB in einen Unterordner im gegenwärtigen Verzeichnis herunter.
Beim Aufruf des Scripts kann eine Backup-Datei der Datenbank übergeben werden (unten: `database_backup`), worauf die
Datenbank in der neuen Installation sofort wiederhergestellt wird.

```shell
sudo apt update -qq && sudo apt install -qq -y curl
curl -fsSL https://gist.githubusercontent.com/Actionb/76babf08b35acc0f94a679e63d979d3a/raw/706b9c22efc46200d066e6307b861868ad9ed359/get-mizdb.sh -o get-mizdb.sh
sh get-mizdb.sh database_backup
```

Die Seite sollte nun unter `http://<hostname>/miz/` erreichbar sein.

## Manuell

1. Docker installieren: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
2. Docker Post-Install Schritte
   durchführen: [https://docs.docker.com/engine/install/linux-postinstall/](https://docs.docker.com/engine/install/linux-postinstall/)
3. MIZDB installieren:

```shell
# Git installieren:
sudo apt update -qq 
sudo apt install -y git
# Repository holen:
git clone https://github.com/Actionb/MIZDB 
cd MIZDB
# Konfigurieren und Docker Umgebung vorbereiten:
sh setup.sh
# Docker Container erstellen und starten: 
docker compose up -d
# Statische Dateien sammeln:
bash mizdb.sh collectstatic
# Log-Verzeichnis Besitzer einrichten:
docker exec -i mizdb-app chown -R apache:apache logs
```

Wenn eine Backup-Datei (hier: `database_backup`) vorhanden ist, kann die Datenbank wiederhergestellt werden:

```shell
bash mizdb.sh restore database_backup
```

Ansonsten müssen die Datenbank Migrationen ausgeführt werden:

```shell
bash mizdb.sh migrate
```

Die Seite sollte nun unter `http://<hostname>/miz/` erreichbar sein.
