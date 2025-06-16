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
