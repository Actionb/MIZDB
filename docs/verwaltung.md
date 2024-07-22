Verwaltung
=======

Für die Verwaltung der Anwendung steht das Programm `mizdb.sh` im MIZDB Verzeichnis zur Verfügung:

```shell
cd MIZDB_VERZEICHNIS && bash mizdb.sh help
```

Wurde MIZDB mithilfe [des Scripts](install.md#per-script) erstellt, so steht systemweit der Befehl `mizdb` zu Verfügung:

```shell
mizdb help
```

Dieser kann anstelle von `bash mizdb.sh` verwendet werden (also z.B. `mizdb reload` anstelle
von `bash mizdb.sh reload`).

## Befehle

### Docker Container & Webserver

* [Container starten](https://docs.docker.com/engine/reference/commandline/compose_up/): `bash mizdb.sh start`
* [Container stoppen](https://docs.docker.com/engine/reference/commandline/compose_down/): `bash mizdb.sh stop`
* [Container neustarten](https://docs.docker.com/engine/reference/commandline/restart/): `bash mizdb.sh restart`
* [Webserver neuladen](https://httpd.apache.org/docs/current/stopping.html#graceful): `bash mizdb.sh reload`

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

### Update

Um die Anwendung zu aktualisieren, benutze:

```shell
bash mizdb.sh update
```

Um die Änderungen für die Benutzer sichtbar zu machen, lade den Webserver neu:

```shell
bash mizdb.sh reload
```

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
