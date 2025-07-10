Verwaltung
=======

Wurde MIZDB mithilfe [des Scripts](install.md) erstellt, so steht der Befehl `mizdb` zu Verfügung:

```shell
mizdb help
```

Ansonsten kann `mizdb.sh` im MIZDB Verzeichnis (standardmäßig `~/.local/share/MIZDB`) auch direkt benutzt werden:

```shell
cd MIZDB_VERZEICHNIS && bash mizdb.sh help
```

## Befehle

### Docker Container & Webserver

* [Container starten](https://docs.docker.com/engine/reference/commandline/compose_up/): `mizdb start`
* [Container stoppen](https://docs.docker.com/engine/reference/commandline/compose_down/): `mizdb stop`
* [Container neustarten](https://docs.docker.com/engine/reference/commandline/restart/): `mizdb restart`
* [Webserver neuladen](https://httpd.apache.org/docs/current/stopping.html#graceful): `mizdb reload`

Mit [docker ps](https://docs.docker.com/engine/reference/commandline/ps/) `docker ps` kann der Zustand der Container
ermittelt werden.  
Der Name des Containers der App ist `mizdb-app` und der Name des Containers der PostgreSQL Datenbank
ist `mizdb-postgres`.

### Update

Um die Anwendung zu aktualisieren, benutze:

```shell
mizdb update
```

[comment]: <> (@formatter:off)  
!!! warning "Achtung: Während des Updates ist die Anwendung für die Benutzer nicht verfügbar!"  
  
[comment]: <> (@formatter:on)

### Datenbank wiederherstellen ([pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html))

Um die Daten der Datenbank aus einer Backup-Datei wiederherzustellen, benutze:

```shell
mizdb restore backup_datei 
```

### Backup erstellen ([pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html))

Um eine Backup-Datei zu erstellen, benutze:

```shell
mizdb dump backup_datei
```

Wird keine Datei als Argument übergeben, so wird eine Backup-Datei im Unterverzeichnis `MIZDB/dumps` erstellt.

## Backups automatisieren

### Cronjob

Mit cronjob kann das Erstellen von Backups automatisiert werden. Dabei wird zu vordefinierten Zeiten ein Skript
ausgeführt, dass die Backups erstellt. Ein solches Skript könnte so aussehen:

```shell
#!/bin/sh  
# This script manages regular backups of the data of the MIZDB database.  
#  
# Use this in a cronjob (on the host machine of the docker container):  
# > crontab -e  
# > 51 7,11,16 * * 1-5  /path/to/mizdb_backup.sh  

BACKUP_DIR="/var/lib/mizdb/backups"  
# Numbers of days you want to keep copies of your database:  
number_of_days=30  
  
file="${BACKUP_DIR}/mizdb_$(date +%Y_%m_%d_%H_%M_%S)"  
docker exec -i mizdb-postgres /bin/sh -c 'pg_dump --username="$POSTGRES_USER" --host=localhost -Fc "$POSTGRES_DB"' > "$file"
  
# Delete older backup copies:  
find "$BACKUP_DIR" -name "mizdb_*" -type f -mtime +$number_of_days -delete
```

Dieses Skript, beispielsweise `mizdb_backup.sh` genannt, erzeugt ein Backup, legt es in `/var/lib/mizdb/backups` ab und
löscht Backups, die älter als 30 Tage sind.

Um es zu aktivieren, zunächst den crontab des root users öffnen:

```shell
sudo crontab -e
```

Und folgenden cronjob hinzufügen:

```
# Backup der MIZDB Datenbank erstellen (Wochentags, um 7:51, 11:51 und 16:51 Uhr):
51 7,11,16 * * 1-5  /bin/sh /path/to/mizdb_backup.sh  
```

### rclone

Mit rclone sync und cronjob kann das Hochladen der Backups auf ein Google Drive automatisiert werden.

1. rclone installieren: [https://rclone.org/install/](https://rclone.org/install/)
2. rclone für Google Drive konfigurieren: [https://rclone.org/drive/](https://rclone.org/drive/)
3. crontab öffnen:

```shell
sudo crontab -e
```

und dann den cronjob definieren, zum Beispiel:

```shell
# Backups mit rclone hochladen:
53 7,11,16 * * 1-5  rclone --config=/path/to/rclone.conf sync /var/lib/mizdb/backups <remote_name>:backups
```

Die Standardkonfiguration erfordert einen Webbrowser.
Um rclone ohne Webbrowser (z.B. für einen headless Server) zu
konfigurieren: [https://rclone.org/remote_setup/](https://rclone.org/remote_setup/)

#### rclone mit Google Service Account

Alternativ kann über einen Service Account auf den Backup-Ordner zugegriffen werden:

[https://rclone.org/drive/#service-account-support](https://rclone.org/drive/#service-account-support)

Als Beispiel, Upload zum existierenden Backup-Drive auf mizdbbackup@gmail.com:

1. Falls nicht der bereits existierende Service "dbbackup-service" benutzt werden soll, muss
   vorerst ein Service Account angelegt werden:
    1. in die Google Cloud Console einloggen: [https://console.cloud.google.com](https://console.cloud.google.com)
    2. Service Accounts > Create Service Account
    3. im Drive Ordner rechts in den Ordnerdetails unter "Zugriff verwalten" den Backup-Ordner für den neuen Service
       Account freigeben

2. Service Account Key (`credentials.json`) generieren, falls nicht vorhanden:
    1. in die Google Cloud Console einloggen: [https://console.cloud.google.com](https://console.cloud.google.com)
    2. Service Accounts > dbbackup-service > KEYS
    3. Mit "ADD KEY" wird ein neuer Key erzeugt und heruntergeladen

3. Root Folder ID des Backup-Ordners herausfinden:
    1. In Google Drive einloggen
    2. Unter "Meine Ablage" den entsprechenden Ordner anklicken
    3. die ID ist am Ende der URL nach `/folders/` zu finden;  
       also z.B. `https://drive.google.com/drive/u/1/folders/foo1bar` hat die ID `foo1bar`

4. rclone Konfigurationsdatei
   erzeugen: [https://rclone.org/drive/#service-account-support](https://rclone.org/drive/#service-account-support)

Mit einer solchen rclone.conf, zu finden unter `/home/my_user/.config/rclone/`:

```
[dbbackup]
type = drive
scope = drive
root_folder_id = foo1bar
service_account_file = /pfad/zu/service/account/credentials.json
```

müsste der cronjob so aussehen:

```
53 7,11,16 * * 1-5  rclone --config=/home/my_user/.config/rclone/rclone.conf sync /var/lib/mizdb/backups dbbackup:/
```

Weitere Links:

* [Gdrive access via service account](https://forum.rclone.org/t/gdrive-access-via-service-account/17926)

## Webserver Einhängepunkt ändern

Standardmäßig ist die Seite der Datenbank unter `http://<ServerName>/miz` erreichbar, d.h. der Einhängepunkt ist `/miz`.
Um einen anderen Einhängepunkt festzulegen, muss in der Datei `docker-compose.env` der Wert für `MOUNT_POINT` geändert
werden. Anschließend müssen die Container gestoppt und neu gestartet werden:

```shell
mizdb restart
```

## Django Shell & psql

Um den interaktiven Python Interpreter für die MIZDB App zu öffnen:  
`bash mizdb shell` und dann `python manage.py shell`

Um das interaktive PostgreSQL Terminal zu öffnen:  
`bash mizdb dbshell` und dann `psql --user=$POSTGRES_USER $POSTGRES_DB`
