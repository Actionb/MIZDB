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

## Installation ohne Docker

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
```

### PostgreSQL Terminal aufrufen

```shell
psql --username=mizdb_user --host=localhost mizdb
```
