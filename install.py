#!/usr/bin/env python3

import argparse
import getpass
import os
import shlex
import sys

from pathlib import Path
from subprocess import run


MIN_POSTGRES_VERSION = 13

# noinspection SpellCheckingInspection
app_config = """# Konfigurationsdatei für die MIZDB Datenbank App.

# Der Secret Key ist eine zufällige Zeichenfolge, die für kryptografische
# Signierung verwendet wird. Ein neuer Schlüssel kann mit diesem Befehl
# generiert werden (auszuführen in der virtuellen Umgebung!):
# python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'
SECRET_KEY: '{secret}'

# Der Hostname des Servers muss zur Liste hinzugefügt werden:
# z.B.: ['localhost', '127.0.0.1', 'archivserv']
ALLOWED_HOSTS: ['{host}']

# Benutzername und Passwort des erstellten Datenbankbenutzers, dem die
# Datenbank gehört:
DATABASE_USER: '{db_user}'
DATABASE_PASSWORD: '{db_password}'
# Weitere Datenbankeinstellungen:
DATABASE_NAME: '{db_name}'
DATABASE_HOST: 'localhost'
DATABASE_PORT: '{port}'

# Adresse zur Wiki:
WIKI_URL: 'http://{host}/wiki/Hauptseite'
"""

# noinspection SpellCheckingInspection
site_config = """
<Macro VHost \$VENV_ROOT \$PROJECT_ROOT>
    <VirtualHost *:80>
        # Name of the host. The name must be included in the ALLOWED_HOSTS django settings.
        ServerName {host}

        # http://{host}/miz/admin/ will produce the admin dashboard.
        # For {host}/foobar/admin/ use:
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
USE VHost {venv_directory} {project_directory}

# Undefine and free up the variable (basically).
UndefMacro VHost
"""


parser = argparse.ArgumentParser(description="MIZDB installieren.")
parser.add_argument('-V', '--venv', dest='venv_directory',
                    help="Pfad zur virtuellen Umgebung")
parser.add_argument('-P', '--port', default=5432,
                    help="Port des Datenbankservers (Standard: »5432«)")
parser.add_argument('-H', '--host', default='localhost',
                    help="Hostname des Datenbankservers (Standard: »localhost«)")
parser.add_argument('--db-name', default='mizdb', dest='db_name',
                    help="Datenbank-Name (Standard: »mizdb«)")
parser.add_argument('--db-user', default='mizdb', dest='db_user',
                    help="Datenbank-Benutzername (Standard: »mizdb«)")


class InstallationAborted(Exception):

    default_message = "Installation abgebrochen."

    def __init__(self, msg: str = '') -> None:
        if msg:
            error_message = f"{self.default_message}\n{msg}"
        else:
            error_message = self.default_message
        super().__init__(error_message)


def _run(_cmd, raise_on_error=True, **kwargs):
    cmd = run(shlex.split(_cmd), **kwargs)
    if cmd.returncode:
        print("")
        if raise_on_error:
            raise InstallationAborted(cmd.stderr.decode())
        else:
            print("WARNUNG:")
            print(cmd.stderr.decode())
    return cmd


def confirm(prompt):
    try:
        return input(prompt) in ('J', 'j', 'ja', 'y', 'Y', 'yes')
    except KeyboardInterrupt:
        print("")
        raise InstallationAborted()


def password_prompt():
    while True:
        try:
            db_password = shlex.quote(getpass.getpass(
                "Geben Sie das Passwort für den neuen Datenbankbenutzer ein: "))
            if db_password == shlex.quote(getpass.getpass("Geben Sie es noch einmal ein: ")):
                return db_password
            else:
                print("Passwörter stimmten nicht überein.", end="\n\n")
        except KeyboardInterrupt:
            print("")
            raise InstallationAborted()


def install_system_packages():
    print("Installiere notwendige Pakete...")
    _run('sudo apt update')
    _run(
        "sudo apt install "
        "apache2 apache2-dev python3-dev python3-venv python3-pip postgresql-contrib libpq-dev"
    )
    print("Fertig!", end="\n\n")


def check_postgres_server(port):
    # Check that the postgres server on the given port has the correct version.
    #
    # Return a boolean indicating whether database migrations can be applied.
    print("Prüfe PostgreSQL...", end="", flush=True)
    cmd = _run(
        f'sudo -u postgres psql --port={port!s} -c "SHOW server_version;"',
        capture_output=True
    )
    # psql will return a string such as this:
    # server_version \n----------------------------------\n 14.1
    # (Ubuntu 14.1-2.pgdg20.04+1)\n(1 Zeile)\n\n
    query_result = cmd.stdout.decode()
    try:
        version_number = float(query_result.split()[2])
    except (IndexError, ValueError):
        # Unexpected query_result.
        version_number = 0
    can_migrate = True
    if version_number < MIN_POSTGRES_VERSION:
        print(
            f"\nPostgreSQL Version {MIN_POSTGRES_VERSION} oder neuer wird benötigt, "
            f"aber auf Port {port!s} liegt folgende Version vor:\n"
            f"{query_result}"
        )
        if confirm(
            "Trotzdem fortfahren? (Hinweis: Datenbankmigrationen werden dann "
                "nicht angewandt) [J/n] "):
            # Migrations will fail with this postgres version, so skip it.
            can_migrate = False
        else:
            raise InstallationAborted(
                f"PostgreSQL Version {MIN_POSTGRES_VERSION} oder neuer benötigt. "
                "https://www.postgresql.org/download/"
            )
    print("OK.")
    return can_migrate


def create_database(port, db_name, db_user, db_password):
    """
    Create the database user and the database.

    Return a boolean indicating whether database migrations can be applied.
    """
    # Check the server version and status:
    can_migrate = check_postgres_server(port)
    print("Erzeuge Datenbank und Datenbankbenutzer...", end="", flush=True)
    # Need to start the service first, if postgres was only just installed.
    _run('sudo service postgresql start', capture_output=True)
    # Create the user and the database:
    _run(
        'sudo -u postgres psql -c '
        f'"CREATE USER {db_user} CREATEDB ENCRYPTED PASSWORD \'{db_password}\';"',
        capture_output=True, raise_on_error=False
    )
    created_db = _run(
        f"sudo -u postgres createdb {db_name} --owner={db_user}",
        capture_output=True, raise_on_error=False
    )

    if not created_db.returncode:
        print("OK.")
    else:
        print("Fehlgeschlagen.")
    return can_migrate and not created_db.returncode


def create_venv(venv_directory):
    if os.path.exists(venv_directory) and not confirm(
            f"{venv_directory} existiert bereits. Überschreiben? [J/n] "):
        return
    print("Erstelle virtuelle Umgebung...", end="", flush=True)
    _run(f"python3 -m venv {venv_directory}")
    _run(f"{venv_directory}/bin/pip install -qU pip")
    print("OK.")


def install_python_packages(venv_directory, project_directory):
    print("Installiere Python Pakete...", end="", flush=True)
    _run(f"{venv_directory}/bin/pip install -qr {project_directory}/requirements.txt")
    print("OK.")


def create_config(venv_directory, project_directory, port, host, db_name, db_user, db_password):
    """
    Create the config file.

    Return a boolean indicating whether the config was created successfully.
    """
    print("Erzeuge Konfigurationsdatei 'config.yaml'...", end="", flush=True)
    secret = _run(
        f'{venv_directory}/bin/python3 -c '
        '"from django.core.management import utils; print(utils.get_random_secret_key())"',
        capture_output=True, raise_on_error=False
    )
    with open(f"{project_directory}/config.yaml", 'w') as f:
        f.write(
            app_config.format(
                secret=secret.stdout.decode().strip(),
                host=host,
                port=port,
                db_name=db_name,
                db_user=db_user,
                db_password=db_password
            )
        )
    if secret.returncode:
        print("\n Hinweis Konfiguration unvollständig: konnte keinen SECRET_KEY erzeugen.")
        return False
    print("OK.")
    return True


# noinspection SpellCheckingInspection
def install_mod_wsgi(venv_directory, project_directory, host):
    """
    Install mod_wsgi and set up Apache.

    Return the site config for MIZDB used by Apache.
    """
    print("Installiere mod_wsgi und richte Apache ein...")
    _run(f"{venv_directory}/bin/pip install -q mod_wsgi")
    cmd = _run(
        f"sudo {venv_directory}/bin/mod_wsgi-express install-module",
        capture_output=True
    )
    with open('mod_wsgi.load', 'w') as f:
        f.write(cmd.stdout.decode())
    _run("sudo mv mod_wsgi.load /etc/apache2/mods-available/mod_wsgi.load")
    _run("sudo a2enmod -q mod_wsgi macro")
    with open('mizdb.conf', 'w') as f:
        f.write(
            site_config.format(
                host=host,
                venv_directory=venv_directory,
                project_directory=project_directory
            )
        )
    _run("sudo mv mizdb.conf /etc/apache2/sites-available/mizdb.conf")
    _run("sudo a2ensite -q mizdb")
    print("Apache neustarten...")
    _run("sudo -k service apache2 restart")


# noinspection SpellCheckingInspection
def install(venv_directory, port, host, db_name, db_user):
    project_directory = str(Path.cwd())
    if venv_directory:
        venv_directory = str(Path(venv_directory).expanduser().resolve())
    else:
        venv_directory = f"{project_directory}/.venv"

    port = shlex.quote(str(port))
    host = shlex.quote(host)
    db_name = shlex.quote(db_name)
    db_user = shlex.quote(db_user)

    # Print a summary and let the user confirm.
    print("Konfiguration:")
    print(f"Pfad zum MIZDB Ordner: {project_directory}")
    print(f"Pfad zur virtuellen Umgebung: {venv_directory}")
    print(f"Port des Datenbankservers: {port}")
    print(f"Hostname des Datenbankservers: {host}")
    print(f"Datenbank-Name: {db_name}")
    print(f"Datenbank-Benutzername: {db_user}")
    print("\nHinweis: install.py --help für eine Übersicht der Parameter.", end="\n\n")
    if not confirm("Fortfahren? [J/n] "):
        raise InstallationAborted()

    print("\n###################################################################\n")
    install_system_packages()

    print("\n###################################################################\n")
    # Get the password:
    db_password = password_prompt()
    can_migrate = create_database(port, db_name, db_user, db_password)

    print("\n###################################################################\n")
    create_venv(venv_directory)
    install_python_packages(venv_directory, project_directory)

    print("\n###################################################################\n")
    config_created = create_config(
        venv_directory, project_directory, port, host, db_name, db_user, db_password)
    manage = f"{venv_directory}/bin/python3 {project_directory}/manage.py"
    if config_created:
        if can_migrate:
            print("Führe Datenbankmigrationen aus...")
            _run(f"{manage} migrate")
            print("OK.")
        print("Sammele statische Dateien...")
        _run(f"{manage} collectstatic --no-input")
        print("OK.")

    print("\n###################################################################\n")
    install_mod_wsgi(venv_directory, project_directory, host)

    print("\n###################################################################\n")
    print("Installation abgeschlossen!")
    print(f"Pfad zum MIZDB Ordner: {project_directory}")
    print(f"Pfad zur virtuellen Umgebung: {venv_directory}")
    print(f"MIZDB URL: http://{host}/miz/admin")
    print(f"MIZDB Konfigurationsdatei: {project_directory}/config.yaml")
    print(f"Apache Konfiguration der MIZDB Seite: /etc/apache2/sites-available/mizdb.conf")


if __name__ == '__main__':
    try:
        install(**vars(parser.parse_args(sys.argv[1:])))
    except InstallationAborted as e:
        print(e.args[0])
