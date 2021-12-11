# Installation (Debian)
## Mittels Installationsscript
MIZDB unter `~/archiv/MIZDB` installieren:
```
git clone https://github.com/Actionb/MIZDB ~/archiv/MIZDB && bash ~/archiv/MIZDB/install.sh
```
Die virtuelle Umgebung wird standardmäßig in `~/.venv/archiv` installiert. Ein anderer Pfad
kann als Argument an das Script übergeben werden: z.B. `bash install.sh ~/woanders`.

## Manuelle Installation
###  1. Erforderliche Pakete installieren

Paketquellen aktualisieren:  
`sudo apt update`

Danach Apache2, diverse Python3 & PostgreSQL Pakete, git Versionskontrolle installieren:  
`sudo apt install apache2 apache2-dev python3-dev python3-venv python3-pip postgresql-contrib libpq-dev git`


### 2. Postgres Datenbank einrichten

Datenbankbenutzer erstellen: `sudo -u postgres createuser mizdb -P --createdb`  
Datenbank erzeugen: `sudo -u postgres createdb mizdb --owner=mizdb`

Benutzername (hier: `mizdb`) und das verwendete Passwort werden später noch einmal benötigt.



### 3. MIZDB Dateien herunterladen und einrichten

Eine virtuelle Umgebung erstellen:  `python3 -m venv ~/.venv/archiv`

MIZDB git Repository klonen:  `git clone https://github.com/Actionb/MIZDB ~/archiv/MIZDB`

Virtuelle Umgebung aktivieren und zum MIZDB Verzeichnis navigieren:  
`source ~/.venv/archiv/bin/activate && cd ~/archiv/MIZDB`

#### MIZDB Konfigurationsdatei einrichten:
Im Unterverzeichnis `MIZDB/settings` (also `~/archiv/MIZDB/MIZDB/settings`) befindet sich eine Vorlage der Konfigurationsdatei: `config_template.yaml`.
Diese sollte in das Grundverzeichnis kopiert und in `config.yaml` umbenannt werden:  
`cp MIZDB/settings/config_template.yaml config.yaml`  

Danach müssen in dieser Datei Angaben zu `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_USER`, `DATABASE_PASSWORD` gemacht werden - Erklärungen sind in der Datei selber zu finden.
Wird bei `WIKI_URL` nichts eingetragen, werden auf den Seiten keine Links zur Wiki eingefügt.

#### Python Module installieren:
Erforderliche Python Module installieren:  
`pip install -r requirements.txt`  
Datenbank Migrationen anwenden:  
`python manage.py migrate`  
Statische Dateien für die Webseite sammeln:  
`python manage.py collectstatic`  


### 4. mod_wsgi installieren

mod_wsgi installieren: `pip install mod_wsgi`  
Den Loader für das mod_wsgi Module für Apache erstellen:  
`sudo ~/.venv/archiv/bin/mod_wsgi-express install-module | sudo tee /etc/apache2/mods-available/mod_wsgi.load > /dev/null`  
Danach kann das Modul aktiviert werden: `sudo a2enmod mod_wsgi`   
Die virtuelle Umgebung kann nun deaktiviert werden: `deactivate`.


### 5. Apache einrichten

Zunächst muss ein zusätzliches Modul aktiviert werden:  
`sudo a2enmod macro`  
Danach Konfigurationsdatei für die MIZDB-Seite erstellen:  
`sudoedit /etc/apache2/sites-available/mizdb.conf`  
Mit folgendem Code:  
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
USE VHost /home/<user>/.venv/archiv /home/<user>/archiv/MIZDB

# Undefine and free up the variable (basically).
UndefMacro VHost
```
Notwendige Angaben:
* `ServerName`: der Hostname des Servers - dieser Name muss auch in der Konfigurationsdatei `config.yaml` 
unter `ALLOWED_HOSTS` gelistet werden.
* `USE VHOST`: benötigt einml den Pfad zum Verzeichnis, in welchem die virtuelle Umgebung erstellt, wurde 
und den Pfad zum Verzeichnis, in welchem die MIZDB Dateien liegen.  
Beispielsweise: `USE VHost /home/sysad/.venv/archiv /home/sysad/archiv/MIZDB`


MIZDB-Seite laden: `sudo a2ensite mizdb`  
Apache neu starten: `sudo service apache2 restart`   
Jetzt sollte MIZDB unter `http://<ServerName>/miz/admin` (also z.B `http://localhost/miz/admin`) erreichbar sein.

### (Optional) MIZDB testen

Zuerst Umgebung aktivieren `source ~/.venv/archiv/bin/activate && cd ~/archiv/MIZDB`, dann Testlauf starten:  
`python manage.py test --keepdb`

### (Optional) Postgres Benutzer Authentifizierung einrichten
Damit man sich als der erstellte Datenbankbenutzer bei Postgres anmelden kann, muss die Datei 
`pg_hba.conf` im entsprechenden Postgres Datenverzeichnis (also z.B.: `/etc/postgresql/13/main/pg_hba.conf`) 
geändert werden.
Am Ende der Datei befindet sich dieser Abschnitt hier:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     peer
```
Ein Eintrag für den Datenbankbenutzer muss hinzugefügt werden.
Hier lautet der Name der Datenbank `mizdb` und der Name des erstellten Benutzers `mizdb`:
```
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   mizdb           mizdb                                   md5
local   all             all                                     peer
```
Anmerkung: wenn für den Benutzer kein Passwort verwendet wird, muss die 
Authentifizierungsmethod von `md5` zu `trust` geändert werden.  

Danach kann man sich mit `psql --username=mizdb --dbname=mizdb` mit der Datenbank verbinden. 