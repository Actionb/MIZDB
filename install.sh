#!/bin/bash
PROJ_DIR=$(realpath "$(dirname "$0")")
if [ "$EUID" -ne 0 ]; then 
    # Not running as root; put the venv in the user's home directory.
    VENV_DIR=${1:-"$HOME/.venv/archiv"}
else
    # Running as root; put the venv in the parent directory of the project.
    VENV_DIR=${1:-"$(dirname "$PROJ_DIR")/.venv/archiv"}
fi
# Start a sudo session:
sudo echo

echo "Pfad zum MIZDB Ordner: $PROJ_DIR"
echo "Pfad zur virtuellen Umgebung: $VENV_DIR"

# Ask for host name and database values:
read -rp "Geben sie den Hostnamen des Servers ein (default: 'localhost'): " host
host=${host:-localhost}
read -rp "Geben Sie einen Namen für die Datenbank ein (default: 'mizdb'): " db_name
db_name=${db_name:-mizdb}
read -rp "Geben Sie den Benutzernamen des Datenbankbenutzers ein (default: 'mizdb'): " db_user
db_user=${db_user:-mizdb}
while true
do
    read -rsp "Geben Sie das Passwort des neuen Datenbankbenutzers ein: " db_password
    if ! [ "$db_password" ]; then
        echo
        echo "Hinweis: Passwort darf nicht leer sein."
        continue
    fi
    echo
    read -rsp "Geben Sie es noch einmal ein: " confirmation
    echo
    if [ "$db_password" == "$confirmation" ]; then
        echo
        break
    else 
        echo "Passwörter stimmten nicht überein."
        echo
    fi
done

# Install required packages:
echo "Installiere notwendige Pakete..."
sudo apt update 
packages="apache2 apache2-dev python3-dev python3-venv python3-pip postgresql-contrib libpq-dev git"
if sudo apt install $packages; then
    echo "Fertig!"
else
    exit
fi

# Create the database and the user:
echo -n "Erzeuge Datenbank und Datenbankbenutzer..."
sudo -u postgres psql -qc "CREATE USER $db_user CREATEDB ENCRYPTED PASSWORD '$db_password';"
sudo -u postgres createdb "$db_name" --owner="$db_user"
echo "OK."

# Create the virtual environment and install the required python packages:
echo -n "Erstelle virtuelle Umgebung..."
python3 -m venv "$VENV_DIR"
# Try to update pip:
"$VENV_DIR"/bin/pip install -qU pip
echo "OK."

echo -n "Installiere Python Pakete..."
if "$VENV_DIR"/bin/pip install -qr "$PROJ_DIR"/requirements.txt; then
    echo "OK."
else
    exit
fi

# Create the MIZDB config file:
echo -n "Erzeuge Konfigurationsdatei 'config.yaml'..."

secret=$("$VENV_DIR"/bin/python -c 'from django.core.management import utils; print(utils.get_random_secret_key())')

cat << EOF > "$PROJ_DIR"/config.yaml
# Konfigurationsdatei für die MIZDB Datenbank App.

# Der Secret Key ist eine zufällige Zeichenfolge, die für kryptografische
# Signierung verwendet wird. Ein neuer Schlüssel kann mit diesem Befehl
# generiert werden (auszuführen in der virtuellen Umgebung!):
# python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'
SECRET_KEY: '$secret'

# Der Hostname des Servers muss zur Liste hinzugefügt werden:
# z.B.: ['localhost', '127.0.0.1', 'archivserv']
ALLOWED_HOSTS: ['$host']

# Benutzername und Passwort des erstellten Datenbankbenutzers, dem die
# Datenbank gehört:
DATABASE_USER: '$db_user'
DATABASE_PASSWORD: '$db_password'

# Adresse zur Wiki:
WIKI_URL: ''

# ---- Weitere, optionale Einstellungen ----

DATABASE_NAME: '$db_name'
DATABASE_HOST: 'localhost'
DATABASE_PORT: ''
EOF
echo "OK."

# Prepare the database and the static files:
echo "Führe Datenbankmigrationen aus..."
"$VENV_DIR"/bin/python "$PROJ_DIR"/manage.py migrate
echo
echo "Sammele statische Dateien..."
"$VENV_DIR"/bin/python "$PROJ_DIR"/manage.py collectstatic --no-input
echo

# Install mod_wsgi and set up Apache:
echo "Installiere mod_wsgi und richte Apache ein..."
"$VENV_DIR"/bin/pip install -q mod_wsgi
sudo "$VENV_DIR"/bin/mod_wsgi-express install-module | sudo tee /etc/apache2/mods-available/mod_wsgi.load > /dev/null

sudo a2enmod -q mod_wsgi
sudo a2enmod -q macro

site_config=/etc/apache2/sites-available/mizdb.conf
cat << EOF | sudo tee $site_config > /dev/null
<Macro VHost \$VENV_ROOT \$PROJECT_ROOT>
	<VirtualHost *:80>  
		# Name of the host. The name must be included in the ALLOWED_HOSTS django settings.
		ServerName $host
	
		# http://localhost/admin/ will produce the admin dashboard.
		# For localhost/foobar/admin/ use:
		# 	WSGIScriptAlias /foobar \$PROJECT_ROOT/MIZDB/wsgi.py
 		WSGIScriptAlias /miz \$PROJECT_ROOT/MIZDB/wsgi.py

 		# python-home must point to the root folder of the virtual environment.
 		# python-path adds the given path to sys.path thereby making packages contained within available for import;
 		# add the path to the django project so the project settings can be imported.
 		WSGIDaemonProcess mizdb python-home=\$VENV_ROOT python-path=\$PROJECT_ROOT
 		WSGIProcessGroup mizdb

 		# Make the static folder in the project root available. The Alias is required.
		Alias /static \$PROJECT_ROOT/static
    		<Directory \$PROJECT_ROOT/static>
        		Require all granted
    		</Directory>

		# Allow access to the file containing the wsgi application.
    		<Directory \$PROJECT_ROOT/MIZDB>
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
USE VHost $VENV_DIR $PROJ_DIR

# Undefine and free up the variable (basically).
UndefMacro VHost 
EOF

sudo a2ensite -q mizdb
echo 
echo "Apache neustarten..."
sudo -k service apache2 restart

echo
echo "Installation abgeschlossen!"
echo "Pfad zum MIZDB Ordner: $PROJ_DIR"
echo "Pfad zur virtuellen Umgebung: $VENV_DIR"
echo "MIZDB URL: http://$host/miz/admin"
echo "MIZDB Konfigurationsdatei: $PROJ_DIR/config.yaml"
echo "Apache Konfiguration der MIZDB Seite: $site_config"
