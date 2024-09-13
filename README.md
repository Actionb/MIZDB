# MIZDB - Musikarchiv Datenbank

Datenbankverwaltung für das Musikarchiv http://miz-ruhr.de/

[comment]: <> (@formatter:off)  
<!-- TOC -->
* [MIZDB - Musikarchiv Datenbank](#mizdb---musikarchiv-datenbank)
  * [Installation Debian (Docker)](#installation-debian-docker)
    * [Per script](#per-script)
    * [Manuell](#manuell)
  * [Verwaltung](#verwaltung)
    * [Docker Container & Webserver](#docker-container--webserver)
    * [Datenbank wiederherstellen (pg_restore)](#datenbank-wiederherstellen-pg_restore)
    * [Backup erstellen (pg_dump)](#backup-erstellen-pg_dump)
    * [Backups automatisieren](#backups-automatisieren)
      * [Cronjob](#cronjob)
      * [rclone](#rclone)
        * [rclone mit Google Service Account](#rclone-mit-google-service-account)
    * [Update](#update)
    * [Django Shell & psql](#django-shell--psql)
    * [Webserver Einhängepunkt ändern](#webserver-einhängepunkt-ändern)
  * [Installation (ohne Docker)](#installation-ohne-docker)
    * [1. Erforderliche Pakete installieren](#1-erforderliche-pakete-installieren)
    * [2. Postgres Datenbank einrichten](#2-postgres-datenbank-einrichten)
    * [3. MIZDB Dateien herunterladen und einrichten](#3-mizdb-dateien-herunterladen-und-einrichten)
      * [Python Module installieren:](#python-module-installieren)
      * [Ordner für Log-Dateien einrichten:](#ordner-für-log-dateien-einrichten)
    * [4. Apache einrichten](#4-apache-einrichten)
    * [Datenbank wiederherstellen](#datenbank-wiederherstellen)
    * [MIZDB testen](#mizdb-testen)
    * [PostgreSQL Terminal aufrufen](#postgresql-terminal-aufrufen)
  * [Deinstallation (Docker)](#deinstallation-docker)
  * [Development](#development)
    * [CSS, Sass & Theme](#css-sass--theme)
    * [Hilfe Seiten erzeugen](#hilfe-seiten-erzeugen)
    * [Release erstellen](#release-erstellen)
<!-- TOC -->
[comment]: <> (@formatter:off)

## Installation Debian (Docker)

### Per script

Das Script installiert Docker und lädt MIZDB in einen Unterordner im gegenwärtigen Verzeichnis herunter.
Beim Aufruf des Scripts kann eine Backup-Datei der Datenbank übergeben werden (unten: `database_backup`), worauf die
Datenbank in der neuen Installation sofort wiederhergestellt wird.

```shell
sudo apt update -qq && sudo apt install -qq -y curl
curl -fsSL https://raw.githubusercontent.com/Actionb/MIZDB/master/scripts/get-mizdb.sh -o get-mizdb.sh
sh get-mizdb.sh database_backup
```

### Manuell

- Docker installieren: https://docs.docker.com/engine/install/
- Docker Post-Install Schritte durchführen: https://docs.docker.com/engine/install/linux-postinstall/
- MIZDB installieren:

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
  docker exec -i mizdb-app python manage.py collectstatic --clear --noinput --skip-checks --verbosity 0  
  # Log-Verzeichnis Besitzer einrichten:
  docker exec -i mizdb-app sh -c 'chown -R apache:apache $LOG_DIR'
  ```

Wenn eine Backup-Datei (hier: `database_backup`) vorhanden ist, kann die Datenbank wiederhergestellt werden:

```shell
bash mizdb.sh restore database_backup
```

Ansonsten müssen die Datenbank Migrationen ausgeführt werden:

```shell
bash mizdb.sh migrate
```

## Verwaltung

Für die Verwaltung der Anwendung steht das Programm `mizdb.sh` im MIZDB Verzeichnis zur Verfügung:

```shell
cd MIZDB_VERZEICHNIS && bash mizdb.sh help
```

Wurde MIZDB mithilfe [des Scripts](#per-script) erstellt, so steht systemweit der Befehl `mizdb` zu Verfügung:

```shell
mizdb help
```

Dieser kann anstelle von `bash mizdb.sh` verwendet werden (also z.B. `mizdb reload` anstelle
von `bash mizdb.sh reload`).

### Docker Container & Webserver

[Container starten](https://docs.docker.com/engine/reference/commandline/compose_up/): `bash mizdb.sh start`  
[Container stoppen](https://docs.docker.com/engine/reference/commandline/compose_down/): `bash mizdb.sh stop`  
[Container neustarten](https://docs.docker.com/engine/reference/commandline/restart/): `bash mizdb.sh restart`  
[Webserver neuladen](https://httpd.apache.org/docs/current/stopping.html#graceful): `bash mizdb.sh reload`

Mit [docker ps](https://docs.docker.com/engine/reference/commandline/ps/) `docker ps` kann der Zustand der Container
ermittelt werden.  
Der Name des Containers der App ist `mizdb-app` und der Name des Containers der PostgreSQL Datenbank
ist `mizdb-postgres`.

### Datenbank wiederherstellen ([pg_restore](https://www.postgresql.org/docs/current/app-pgrestore.html))

Um die Daten der Datenbank aus einer Backup-Datei wiederherzustellen, benutze:

```shell
bash mizdb.sh restore backup_datei 
```

### Backup erstellen ([pg_dump](https://www.postgresql.org/docs/current/app-pgdump.html))

Um eine Backup-Datei zu erstellen, benutze:

```shell
bash mizdb.sh dump backup_datei
```

Wird keine Datei als Argument übergeben, so wird eine Backup-Datei im Unterverzeichnis `MIZDB/dumps` erstellt.

### Backups automatisieren

#### Cronjob

Crontab des root users öffnen:

```shell
sudo crontab -e
```

Und folgenden cronjob hinzufügen:

```
# Backup der MIZDB Datenbank erstellen (Wochentags, um 7:51, 11:51 und 16:51 Uhr):
51 7,11,16 * * 1-5  docker exec mizdb-postgres sh /mizdb/backup.sh
```

#### rclone

Mit rclone sync und cronjob kann das Hochladen der Backups auf ein Google Drive automatisiert werden.

1. rclone installieren: https://rclone.org/install/
2. rclone für Google Drive konfigurieren: https://rclone.org/drive/
3. crontab öffnen:
    ```shell
    sudo crontab -e
    ```
   und dann den cronjob definieren, zum Beispiel:
    ```shell
   # Backups mit rclone hochladen:
    53 7,11,16 * * 1-5  rclone --config=/path/to/rclone.conf sync /path/to/mizdb/backups <remote_name>:backups
    ```

Die Standardkonfiguration erfordert einen Webbrowser.
Um rclone ohne Webbrowser (z.B. für einen headless Server) zu konfigurieren: https://rclone.org/remote_setup/

##### rclone mit Google Service Account

Alternativ kann über einen Service Account auf den Backup-Ordner zugegriffen werden:

https://rclone.org/drive/#service-account-support

Als Beispiel, Upload zum existierenden Backup-Drive auf mizdbbackup@gmail.com:

1. Falls nicht der bereits existierende Service "dbbackup-service" benutzt werden soll, muss
   vorerst ein Service Account angelegt werden:
   1. in die Google Cloud Console einloggen: https://console.cloud.google.com
   2. Service Accounts > Create Service Account
   3. im Drive Ordner rechts in den Ordnerdetails unter "Zugriff verwalten" den Backup-Ordner für den neuen Service
      Account freigeben

2. Service Account Key (`credentials.json`) generieren, falls nicht vorhanden:
   1. in die Google Cloud Console einloggen: https://console.cloud.google.com
   2. Service Accounts > dbbackup-service > KEYS
   3. Mit "ADD KEY" wird ein neuer Key erzeugt und heruntergeladen

3. Root Folder ID des Backup-Ordners herausfinden:
   1. In Google Drive einloggen
   2. Unter "Meine Ablage" den entsprechenden Ordner anklicken
   3. die ID ist am Ende der URL nach `/folders/` zu finden; also
      z.B. https://drive.google.com/drive/u/1/folders/10z55r6HFxfOWkmrRIT4-mrjhhJgqYPqa hat die
      ID `10z55r6HFxfOWkmrRIT4-mrjhhJgqYPqa`

4. rclone Konfigurationsdatei erzeugen: https://rclone.org/drive/#service-account-support

Mit einer solchen rclone.conf, zu finden unter `/home/my_user/.config/rclone/`:

```
[dbbackup]
type = drive
scope = drive
root_folder_id = 10z55r6HFxfOWkmrRIT4-mrjhhJgqYPqa
service_account_file = /pfad/zu/service/account/credentials.json
```

müsste der cronjob so aussehen:

```
53 7,11,16 * * 1-5  rclone --config=/home/my_user/.config/rclone/rclone.conf sync /var/lib/mizdb/backups dbbackup:/
```

Weitere Links: [Gdrive access via service account](https://forum.rclone.org/t/gdrive-access-via-service-account/17926)

### Update

Um die Anwendung zu aktualisieren, benutze:

```shell
bash mizdb.sh update
```

> [!WARNING]  
> Achtung: Während des Updates ist die Anwendung für die Benutzer nicht verfügbar!"

### Django Shell & psql

Um den interaktiven Python Interpreter für die MIZDB App zu öffnen:  
`bash mizdb shell` und dann `python manage.py shell`

Um das interaktive PostgreSQL Terminal zu öffnen:  
`bash mizdb dbshell` und dann `psql --user=$POSTGRES_USER $POSTGRES_DB`

### Webserver Einhängepunkt ändern

Standardmäßig ist die Seite der Datenbank unter `http://<ServerName>/miz` erreichbar, d.h. der Einhängepunkt ist `/miz`.
Um einen anderen Einhängepunkt festzulegen, muss in der Datei `.env` der Wert für `MOUNT_POINT` geändert werden.  
Anschließend müssen die Container gestoppt und neu gestartet werden:

```shell
bash mizdb.sh stop && bash mizdb.sh start
```

## Installation (ohne Docker)

**Wichtig:** MIZDB sollte nicht im Home Verzeichnis erstellt werden, da der Webserver keinen Zugriff auf dieses
Verzeichnis hat!
Also zum Beispiel unter `/opt/` erstellen:

```shell
sudo mkdir -p /opt/archiv
sudo chown $USER:$USER /opt/archiv
cd /opt/archiv
``` 

### 1. Erforderliche Pakete installieren

```shell
# Paketquellen aktualisieren:  
sudo apt update
# Danach Apache2, diverse Python3 & PostgreSQL Pakete, git Versionskontrolle installieren:  
sudo apt install apache2 apache2-dev python3-dev python3-venv python3-pip postgresql-contrib libpq-dev git
```

### 2. Postgres Datenbank einrichten

```shell
# Datenbankbenutzer erstellen:
sudo -u postgres createuser mizdb_user -P --createdb  
# Datenbank erzeugen:
sudo -u postgres createdb mizdb --owner=mizdb_user
```

Benutzername (hier: `mizdb_user`) und das verwendete Passwort werden später noch einmal benötigt.

### 3. MIZDB Dateien herunterladen und einrichten

```shell
# MIZDB git Repository klonen:
git clone https://github.com/Actionb/MIZDB .
# Virtuelle Umgebung erstellen und aktivieren:
python3 -m venv venv && source venv/bin/activate
# MIZDB einrichten:
sh setup.sh
```

Das Script `setup.sh` fragt nach einigen Daten für die Applikation und erstellt
die folgenden Dateien:

- im Stammverzeichnis wird die Datei `.env` mit den Werten für Umgebungsvariablen erstellt
- im Unterverzeichnis `.secrets` werden die folgenden Dateien erstellt:
	- `.passwd`: beinhaltet das Passwort der Datenbank
	- `.key`: beinhaltet einen kryptografischen Schlüssel
	- `.allowedhosts`: beinhaltet die erwarteten Hostnamen

#### Python Module installieren:

```shell
# Erforderliche Python Module installieren:  
python3 -m pip install --upgrade pip wheel
python3 -m pip install -r requirements/base.txt  
# Datenbank Migrationen anwenden:  
python manage.py migrate
# Statische Dateien für die Webseite sammeln:  
python manage.py collectstatic --clear --noinput --skip-checks --verbosity 0
```

#### Ordner für Log-Dateien einrichten:

```shell
# Ordner erstellen:
sudo mkdir -p /var/log/mizdb/
# Den Webserver-Benutzer als Besitzer einstellen:
sudo chown www-data:www-data /var/log/mizdb
```

### 4. Apache einrichten

```shell
# Den Loader für das mod_wsgi Module für Apache erstellen:  
sudo venv/bin/mod_wsgi-express install-module | sudo tee /etc/apache2/mods-available/mod_wsgi.load > /dev/null  
# Danach kann das Modul aktiviert werden: 
sudo a2enmod mod_wsgi
# 'macro' Modul aktivieren:  
sudo a2enmod macro
# Danach Konfigurationsdatei für die MIZDB-Seite erstellen:  
sudoedit /etc/apache2/sites-available/mizdb.conf  
```

Folgendem Code in die Konfigurationsdatei einfügen:

```
<Macro VHost $VENV_ROOT $PROJECT_ROOT>
	<VirtualHost *:80>  
		# Name of the host. The name must be included in the ALLOWED_HOSTS django settings.
		ServerName localhost
	
		# http://localhost/admin/ will produce the admin dashboard.
		# For localhost/foobar/admin/ use:
		# 	WSGIScriptAlias /foobar $PROJECT_ROOT/MIZDB/wsgi.py
 		WSGIScriptAlias /miz $PROJECT_ROOT/MIZDB/wsgi.py

 		# python-home must point to the root folder of the virtual environment.
 		# python-path adds the given path to sys.path thereby making packages contained within available for import;
 		# add the path to the django project so the project settings can be imported.
 		WSGIDaemonProcess mizdb python-home=$VENV_ROOT python-path=$PROJECT_ROOT
 		WSGIProcessGroup mizdb

 		# Make the static folder in the project root available. The Alias is required.
		Alias /static $PROJECT_ROOT/static
    		<Directory $PROJECT_ROOT/static>
        		Require all granted
    		</Directory>

		# Allow access to the file containing the wsgi application.
    		<Directory $PROJECT_ROOT/MIZDB>
        		<Files wsgi.py>
            			Require all granted
        		</Files>
    		</Directory>

	</VirtualHost>
</Macro>

# Create the VirtualHost 'VHost' declared above with the following parameters:
#	 - root of the virtual environment
#	 - root of the django project directory
#
# Don't confuse the project directory with the project package directory:
#	- the project directory contains manage.py and the various django apps
#	- the project package is a directory inside the project directory and contains settings.py, wsgi.py and the root urls.py
USE VHost /opt/archiv/venv /opt/archiv

# Undefine and free up the variable (basically).
UndefMacro VHost
```

**⚠️ Notwendige Änderungen ⚠️**:

* In der Zeile mit `ServerName` muss der Hostname des Servers eingefügt werden. Dieser Name muss auch in der `.env`
  Datei unter `ALLOWED_HOSTS` auftauchen.
* In der Zeile `USE VHOST` müssen gegebenenfalls die zwei Pfade angepasst werden.
	* der erste Pfad ist der Pfad zum Verzeichnis der virtuellen Umgebung
	* der zweite Pfad ist der Pfad zum Grundverzeichnis der App, in welchem auch `manage.py` zu finden ist.

	Also beispielsweise: `USE VHost /opt/archiv/venv /opt/archiv`

Danach:

```shell
# MIZDB-Seite aktivieren:
sudo a2ensite mizdb
# Apache neu starten:
sudo service apache2 restart   
```

Jetzt sollte MIZDB unter `http://<ServerName>/miz/admin` (also z.B. http://localhost/miz/admin) erreichbar sein.

### Datenbank wiederherstellen

```shell
sudo -u postgres dropdb mizdb
sudo -u postgres createdb mizdb --owner=mizdb_user
sudo -u postgres pg_restore --dbname mizdb < backup_datei
```

### MIZDB testen

```shell
python manage.py test --settings=tests.settings tests
````

### PostgreSQL Terminal aufrufen

```shell
psql --username=mizdb_user --host=localhost mizdb
```

## Deinstallation (Docker)

Bei der Deinstallation werden folgende Verzeichnisse und Dateien gelöscht:

- das MIZDB Source Verzeichnis
- das Datenbank Verzeichnis (standardmäßig: `/var/lib/mizdb`)
- das Log Verzeichnis (standardmäßig: `/var/log/mizdb`)
- das Management Skript (standardmäßig: `/usr/local/bin/mizdb`)

Außerdem wird der Backup cronjob aus der root crontab entfernt.

Mit Management Skript:

```shell
mizdb uninstall
```

oder aus dem MIZDB Verzeichnis:

```shell
bash mizdb.sh uninstall
```

## Development

Virtuelle Umgebung erstellen:

```shell
python -m venv .venv
echo 'export "DJANGO_DEVELOPMENT=1"' >> .venv/bin/activate
. .venv/bin/activate
```

Zusätzliche Dependencies und Git Hooks installieren:

```shell
pip install -r requirements/dev.txt
npm install
pre-commit install
```

### CSS, Sass & Theme

Benutze

```shell
npm run sass-build
```

oder

```shell
npm run sass-watch
```

Um die CSS Dateien zu erstellen.

Links:

- https://getbootstrap.com/
- https://bootswatch.com/flatly/
- https://sass-lang.com/

### Hilfe Seiten erzeugen

Um die Hilfe Seiten der MIZDB "site" app zu erzeugen, benutze:

```shell
mkdocs build
```

Ein [post build hook](https://www.mkdocs.org/dev-guide/plugins/#on_post_build)
erzeugt aus den mkdocs html Dateien Django Templates und legt sie unter `dbentry/site/templates/help` ab.

### Release erstellen

1. Git-Flow `release` branch erzeugen:
    ```shell
    git flow release start '1.0.1'
    ```
    (siehe [hier](https://www.atlassian.com/de/git/tutorials/comparing-workflows/gitflow-workflow) für mehr Informationen)
2. Versionsdatei aktualisieren.  
    Dazu können Git-Flow Hooks verwendet werden: https://github.com/jaspernbrouwer/git-flow-hooks. 
    Der folgende Befehl installiert die notwendigen Hooks im lokalen git Verzeichnis:
    ```shell
    ./scripts/git-flow-hooks.sh
    ```
    Siehe auch: [Git-Flow Hooks with smartgit](https://smartgit.userecho.com/communities/1/topics/1726-git-flow-support-hooks)
    
    Alternativ steht ein Skript zur Verfügung, um die Versionsdatei zu aktualisieren:
    ```shell
    ./scripts/bump_version.py {major,minor,patch}
    ```
3. `release` branch beenden:
    ```shell
    git flow release finish '1.0.1'
    ```
    
> [!NOTE]  
> Wird git-flow-hooks benutzt, um die Versionsdatei zu aktualisieren, muss bei dem Befehl `git flow release start` keine
> Version angegeben werden; git-flow-hooks ermittelt die neue Version aus der Versionsdatei. 
