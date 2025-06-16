Installation
=======

[comment]: <> (@formatter:off)  
!!! note "Voraussetzungen"  
    Docker und Docker Compose müssen installiert sein.
[comment]: <> (@formatter:on)

## Per Script (empfohlen)

Das Installations-Skript richtet die Docker Container und das Management Werkzeug `mizdb` ein. Außerdem fragt es bei der
Installation, ob die Datenbank aus einem Backup wiederhergestellt werden soll.

```shell
bash -c "$(curl -sSL https://raw.githubusercontent.com/Actionb/MIZDB/master/scripts/install-mizdb.sh)"
```

Nach dem Ausführen des Skripts sollte MIZDB unter [http://localhost/miz/](http://localhost/miz/) verfügbar sein.

## Per Docker Compose

Die Dateien `docker-compose.yaml` und `docker-compose.env` (hier
auf [github](https://github.com/Actionb/MIZDB/tree/master/docker)) in einen Ordner deiner Wahl herunterladen, z.B.:

```shell
curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/docker/docker-compose.yaml" -o docker-compose.yaml
curl -fsSL "https://raw.githubusercontent.com/Actionb/MIZDB/master/docker/docker-compose.env" -o docker-compose.env
```

Anschließend führe folgenden Befehl aus, um die Docker Container zu erzeugen und zu starten:

```shell
docker compose --env-file docker-compose.env up -d
```

Als Nächstes muss noch die Datenbank eingerichtet werden. Dazu kann entweder ein vorhandenes Backup eingelesen werden
oder komplett neue Datenbanktabellen erzeugt werden.

### Backup wiederherstellen

Mit dem folgenden Befehl kann ein Backup der Datenbank mit dem Dateinamen `backup` eingelesen werden:

```shell
docker exec -i mizdb-postgres /bin/sh -c 'export PGUSER="$POSTGRES_USER" && export PGHOST=localhost && dropdb "$POSTGRES_DB" && createdb "$POSTGRES_DB" && pg_restore --dbname "$POSTGRES_DB"' < backup 
```

### Neue Datenbanktabellen erzeugen

Soll kein Backup wiederhergestellt werden, müssen die Datenbanktabellen erzeugt werden:

```shell
docker exec -i mizdb-app python manage.py migrate
```

### Management Werkzeug herunterladen

`mizdb.sh` herunterladen, um die [Verwaltung](verwaltung.md) leichter zu gestalten:

```shell
curl -sSL https://raw.githubusercontent.com/Actionb/MIZDB/master/mizdb.sh -o mizdb.sh
```

Um `mizdb.sh` überall als `mizdb` ausführbar zu machen:

```shell
cat << EOF > ~/.local/bin/mizdb
#!/bin/sh

file=\$(readlink -f "\$2")
cd $(pwd) || exit
bash mizdb.sh "\$1" "\$file"
cd - > /dev/null || exit
EOF
chmod +x ~/.local/bin/mizdb
```

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

### 3. MIZDB Dateien herunterladen

```shell
# MIZDB git Repository klonen:
git clone https://github.com/Actionb/MIZDB .
# Virtuelle Umgebung erstellen und aktivieren:
python3 -m venv venv && source venv/bin/activate
```

Passwort für Datenbank-Benutzer hinterlegen:
```shell
echo 'export "DB_PASSWORD=supersecret"' >> venv/bin/activate
```

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

Folgenden Code in die Konfigurationsdatei einfügen:

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

* In der Zeile mit `ServerName` muss der Hostname des Servers eingefügt werden.
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
