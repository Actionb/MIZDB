# Installation (Debian) 

###  1. Erforderliche Pakete installieren

Paketquellen aktualisieren:  
`sudo apt update`

Danach Apache2, diverse Python3 & PostgreSQL Pakete, git Versionskontrolle installieren:  
`sudo apt install apache2 apache2-dev python3-dev python3-venv python3-pip postgresql-contrib libpq-dev git`


### 2. Postgres Datenbank einrichten

Postgres Terminal aufrufen `sudo -u postgres psql` und User und Datenbank erstellen:  
```
CREATE USER mizdb_user WITH ENCRYPTED PASSWORD 'dein_passwort';
ALTER USER mizdb_user CREATEDB;  -- wird benötigt, um eine Testdatenbank für Tests erstellen zu können
CREATE DATABASE mizdb OWNER mizdb_user;  -- Datenbank erstellen
\q -- Terminal beenden
```
Benutzername (hier: `mizdb_user`) und Passwort (hier: `dein_passwort`) werden später noch einmal benötigt.


### 3. MIZDB Dateien herunterladen und einrichten

Eine virtuelle Umgebung erstellen:  
`sudo python3 -m venv /srv/archiv && cd /srv/archiv/`

MIZDB git Repository klonen:  
`sudo git clone https://github.com/Actionb/MIZDB`

`sudo` übernimmt die virtuelle Umgebung nicht: `sudo pip` würde das globale pip rufen und damit nicht in die virtuelle Umgebung installieren. Somit kann `sudo`nicht benutzt werden und es muss auf `root` gewechselt werden:  
`su root`  
Virtuelle Umgebung aktivieren und zum MIZDB Ordner navigieren:  
`source /srv/archiv/bin/activate && cd /srv/archiv/MIZDB`

#### MIZDB Konfigurationsdatei einrichten:
Im Unterordner `MIZDB/settings` (also `/srv/archiv/MIZDB/MIZDB/settings`) befindet sich eine Vorlage der Konfigurationsdatei: `config_template.yaml`.
Diese sollte kopiert und in `config.yaml` umbenannt werden:  
`cp MIZDB/settings/config_template.yaml config.yaml`  

Danach müssen Angaben zu `SECRET_KEY`, `ALLOWED_HOSTS`, `DATABASE_USER`, `DATABASE_PASSWORD` gemacht werden - Erklärungen sind in der Datei selber zu finden.
Wird bei `WIKI_URL` nichts eingetragen, werden auf den Seiten keine Links zur Wiki angeboten.

#### Python Module installieren:
Erforderliche Python Module installieren:  
`pip install -r requirements.txt`  
Datenbank Migrationen anwenden:  
`python manage.py migrate`  
Statische Dateien für die Webseite sammeln:  
`python manage.py collectstatic`  


### 4. mod_wsgi installieren
mod_wsgi lässt sich in der virtuellen Umgebung mit pip installieren.
Alternativ kann auch direkt vom Quellcode von installiert werden.

### 4.1 mod_wsgi mit pip installieren (empfohlen)

mod_wsgi installieren: `pip install mod_wsgi`  
Jetzt muss apache mitgeteilt werden, wo das Modul liegt. Dazu erstellt man einen Loader, der den Pfad angibt:  
```mod_wsgi-express install-module > /etc/apache2/mods-available/mod_wsgi.load```  
Danach kann das Modul aktiviert werden: `a2enmod mod_wsgi`   
Umgebung deaktivieren `deactivate`und dann Root Rechte ablegen `exit`.

### 4.2 mod_wsgi aus Quellcode installieren
Installationshinweise: https://modwsgi.readthedocs.io/en/master/user-guides/quick-installation-guide.html  
Neueste Version auf: https://github.com/GrahamDumpleton/mod_wsgi/releases

Zunächst virtuelle Umgebung deaktivieren `deactivate` und Root Rechte ablegen `exit`.  
Download (in einen beliebigen Ordner außerhalb vom archiv Ordner) und entpacken, hier beispielsweise mit Version 4.7.1:
```
wget https://github.com/GrahamDumpleton/mod_wsgi/archive/refs/tags/4.7.1.tar.gz
tar xvfz 4.7.1.tar.gz
cd mod_wsgi-4.7.1
```
Installation vorbereiten, Software bauen und installieren (root Rechte nötig):
```
./configure --with-python=/usr/bin/python3
make
make install
```
Ist die Installation erfolgreich, so wird auf den Speicherort des Moduls für Apache hingewiesen. Z.B.:
>"Libraries have been installed in: /usr/lib/apache2/modules"  

Danach aufräumen und Root Rechte ablegen:
```
make clean
exit
```
Damit Apache das wsgi Modul laden kann, muss noch ein Loader erstellt werden:  
`sudo nano /etc/apache2/mods-available/mod_wsgi.load`  
mit folgendem Code:  
`LoadModule wsgi_module /usr/lib/apache2/modules/mod_wsgi.so` 
wobei der Pfad zum Modul dem Speicherort von oben entspricht.  
Danach kann das Modul aktiviert werden: `sudo a2enmod mod_wsgi`

### 5. Apache einrichten

Zunächst muss ein zusätzliches Modul aktiviert werden:  
`sudo a2enmod macro`  
Danach Konfigurationsdatei für die MIZDB-Seite erstellen:  
`sudo nano /etc/apache2/sites-available/mizdb.conf`  
Mit folgendem Code:  
```
<Macro VHost $VENV_ROOT $PROJECT_ROOT>
	<VirtualHost *:80>  
		# Name of the host. The name must be included in the ALLOWED_HOSTS django settings.
		ServerName localhost
	
		# http://localhost/admin/ will produce the admin dashboard.
		# For localhost/foobar/admin/ use:
		# 	WSGIScriptAlias /foobar $PROJECT_ROOT/MIZDB/wsgi.py
 		WSGIScriptAlias / $PROJECT_ROOT/MIZDB/wsgi.py

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
USE VHost /srv/archiv /srv/archiv/MIZDB

# Undefine and free up the variable (basically).
UndefMacro VHost
```

MIZDB-Seite laden: `sudo a2ensite mizdb`  
Apache neu starten: `sudo service apache2 restart`  
Jetzt sollte MIZDB unter `http://localhost/admin` erreichbar sein.

### (Optional) MIZDB testen

Zuerst Umgebung aktivieren `source /srv/archiv/bin/activate && cd /srv/archiv/MIZDB`, dann Testlauf starten:  
`python manage.py test`
