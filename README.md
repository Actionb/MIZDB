# MIZDB - Musikarchiv Datenbank

Datenbankverwaltung für das Archiv für populäre Musik im Ruhrgebiet e.V.

Links:

* [Dokumentation](https://actionb.github.io/MIZDB)
* [Webseite Musikarchiv](http://miz-ruhr.de/)

## Installation

Das Installations-Skript richtet die Docker Container und das Management Programm `mizdb` ein. Außerdem fragt es bei der
Installation, ob die Datenbank aus einem Backup wiederhergestellt werden soll.

> [!NOTE]  
> Docker und Docker Compose müssen installiert sein.

```shell
bash -c "$(curl -sSL https://raw.githubusercontent.com/Actionb/MIZDB/master/scripts/install-mizdb.sh)"
```

Nach dem Ausführen des Skripts sollte MIZDB unter [http://localhost/miz/](http://localhost/miz/) verfügbar sein.

Siehe auch:

* [Source Code des Installations-Scripts](https://github.com/Actionb/MIZDB/blob/master/scripts/install-mizdb.sh)
* [weitere Installationsmöglichkeiten](https://actionb.github.io/MIZDB/install.html)
* [Deinstallation](https://actionb.github.io/MIZDB/deinstall.html)

## Verwaltung

Für die Verwaltung der Anwendung steht das Programm `mizdb.sh` im MIZDB Verzeichnis zur Verfügung:

```shell
cd MIZDB_VERZEICHNIS && bash mizdb.sh help
```

Wurde MIZDB mithilfe des Installations-Skripts erstellt, so steht für den Benutzer der Befehl `mizdb` zu Verfügung:

```shell
mizdb help
```

Dieser kann anstelle von `bash mizdb.sh` verwendet werden (also z.B. `mizdb reload` anstelle
von `bash mizdb.sh reload`).

Weitere Informationen mit einer Auflistung der verfügbaren Befehle gibt es in der
Dokumentation:

* [Verwaltung](https://actionb.github.io/MIZDB/verwaltung.html)

## Development

### Installation

#### System Requirements

* PostgreSQL
    * für [Debian/Ubuntu](https://www.postgresql.org/download/)
    * für [Fedora](https://docs.fedoraproject.org/en-US/quick-docs/postgresql/)
* Apache2 mit Dev Headern (benötigt von mod_wsgi)
* libpq-dev (benötigt von psycopg2)
* Git
* [npm](https://docs.npmjs.com/downloading-and-installing-node-js-and-npm)

Zum Beispiel für Debian:

```shell
sudo apt update && sudo apt install python3-pip python3-venv postgresql apache2-dev libpq-dev git nodejs npm
```

#### Datenbank einrichten

```shell
# Datenbankbenutzer erstellen:
sudo -u postgres createuser mizdb_user -P --createdb
# Datenbank erzeugen:
sudo -u postgres createdb mizdb --owner=mizdb_user
```

> [!NOTE]  
> Es wird empfohlen, für den Datenbankbenutzer das Passwort "mizdb" zu benutzen. Dies ist das Passwort, welches
> standardmäßig von den Docker Containern und den Django Settings für MIZDB benutzt wird.

#### MIZDB installieren

```shell
# Repository klonen:
git clone https://github.com/Actionb/MIZDB MIZDB
cd MIZDB
# Virtuelle Umgebung erstellen:
python3 -m venv .venv
echo 'export "DJANGO_DEVELOPMENT=1"' >> .venv/bin/activate
. .venv/bin/activate
# Projekt Abhängigkeiten und Git Hooks installieren:
pip install -r requirements/dev.txt
npm install
pre-commit install
```

Anschließend entweder die Migrationen ausführen:

```shell
python3 manage.py migrate
```

oder ein Backup einlesen:

```shell
pg_restore --user=mizdb_user --host=localhost --dbname mizdb < backup_datei
```

### Scripts mit Poe ausführen

Mit [Poe The Poet](https://github.com/nat-n/poethepoet) können nützliche, vordefinierte Scripts ausgeführt werden.

Installieren mit [pipx](https://pipx.pypa.io/stable/) (oder
siehe [andere Methoden](https://poethepoet.natn.io/installation.html)):

```shell
pipx install poethepoet
```

Anschließend können einzelne Scripts so ausgeführt werden:

```shell
poe test
```

Die folgenden Scripts sind in `pyproject.toml`
definiert (siehe [Poe Docs - Defining tasks](https://poethepoet.natn.io/tasks/index.html)):

| Script Name    | Beschreibung                                             |
|----------------|----------------------------------------------------------|
| server         | Development Server starten                               |
| shell          | Django Shell starten                                     |
| test           | Pytest Tests ausführen (mit Coverage)                    |
| test-q         | Pytest Tests ausführen (ohne Coverage, schneller)        | 
| test-pw        | Playwright Tests ausführen                               |
| drop-testdb    | Alle Test-Datenbanken löschen                            |
| tox            | Python tox ausführen                                     |
| ruff           | ruff Linter und Formatter ausführen und Probleme beheben |
| ruff-check     | `ruff check .` ausführen                                 |
| build-docs     | Dokumentation bauen und bei Github hochladen             |
| docker-restart | MIZDB Docker Container neustarten                        |
| build          | Docker Image bauen                                       |
| publish        | Docker Image bauen und hochladen                         |

## Docker Container

Wenn man Docker im Project Root ausführen möchte, muss man die Pfade für `docker-compose.yaml` und `docker-compose.env`
angeben, da sich diese Dateien in dem Unterordner `docker` befinden, wo Docker sie nicht sucht.

Dazu sei es empfohlen, in der `activate` Datei der virtuellen Umgebung die Umgebungsvariablen `COMPOSE_FILE` und
`COMPOSE_ENV_FILES` zu setzen:

```shell
export COMPOSE_FILE=./docker/docker-compose.yaml
export COMPOSE_ENV_FILES=./docker/docker-compose.env
```

Alternativ können bei jedem Docker Befehl die Pfade als Argumente übergeben werden:

```shell
docker compose -f ./docker/docker-compose.yaml --env-file=./docker/docker-compose.env up
```

### Dev Server (Docker)

Um den Test-/Development Server zu starten:

```shell
docker compose -f docker-compose.test-server.yaml up --build -d
```

Der Server ist dann unter http://host_name:8090 (lokal: http://127.0.0.1:8090) erreichbar.

### Tests

#### Einfacher Testdurchlauf

Mit coverage und ohne Playwright Tests:

```shell
pytest -n auto -m "not e2e" --cov=. --cov-report html  --cov-branch tests
```

#### Playwright

Die Playwright Browser müssen installiert sein:

```shell
playwright install
```

Dann [Playwright](https://playwright.dev/) Tests auszuführen:

```shell
pytest -n auto --browser firefox tests/test_site/test_playwright
```

#### Tox

Teste MIZDB mit verschiedenen Python-Versionen und den Produktions-Settings:

```shell
tox
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

#### Offline-Hilfe

Um die Hilfe Seiten der MIZDB "site" app zu erzeugen, benutze:

```shell
mkdocs build -f mkdocs-offline.yml
```

Ein [post build hook](https://www.mkdocs.org/dev-guide/plugins/#on_post_build)
erzeugt aus den mkdocs html Dateien Django Templates und legt sie unter `dbentry/site/templates/help` ab.

#### Online-Hilfe

Hilfe Seiten mit dem [Materials Theme](https://squidfunk.github.io/mkdocs-material/) erzeugen und bei Github Pages
hochladen:

```shell
mkdocs gh-deploy -f mkdocs-online.yml
```

### Release erstellen

1. Git-Flow `release` branch erzeugen:
    ```shell
    git flow release start '1.0.1'
    ```
   (siehe [hier](https://www.atlassian.com/de/git/tutorials/comparing-workflows/gitflow-workflow) für mehr
   Informationen)
2. Versionsdatei aktualisieren.  
   Dazu können Git-Flow Hooks verwendet werden: https://github.com/jaspernbrouwer/git-flow-hooks.
   Der folgende Befehl installiert die notwendigen Hooks im lokalen git Verzeichnis:
    ```shell
    ./scripts/git-flow-hooks.sh
    ```
   Siehe
   auch: [Git-Flow Hooks with smartgit](https://smartgit.userecho.com/communities/1/topics/1726-git-flow-support-hooks)

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
