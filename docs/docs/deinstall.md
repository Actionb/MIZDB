Deinstallation
=======

## Deinstallation via mizdb.sh

MIZDB kann mit

```shell
mizdb uninstall
```

oder mit (wenn im MIZDB Verzeichnis):

```shell
bash mizdb.sh uninstall
```

deinstalliert werden.

Bei der Deinstallation werden folgende Verzeichnisse und Dateien gelöscht:

- das MIZDB Source Verzeichnis
- das Datenbank Verzeichnis (standardmäßig: `/var/lib/mizdb`)
- das Log Verzeichnis (standardmäßig: `/var/log/mizdb`)
- das Management Skript (standardmäßig: `/usr/local/bin/mizdb`)

Außerdem wird der Backup cronjob aus der root crontab entfernt.

## Manuelle Deinstallation

Container anhalten, Source Dateien und Management-Skript löschen:

```shell
# Docker Container anhalten:
docker stop mizdb-app mizdb-postgres
# MIZDB Verzeichnis löschen:
sudo rm -rf <PFAD/ZUM/MIZDB_VERZEICHNIS>
# Management-Skript löschen:
sudo rm -f /usr/local/bin/mizdb
```

Datenbank und Logs löschen:

```shell
sudo rm -rf /var/lib/mizdb
sudo rm -rf /var/log/mizdb 
```

Cronjob entfernen:

```shell
sudo crontab -l 2>/dev/null | grep -v 'docker exec mizdb-postgres sh /mizdb/backup.sh' | grep -v "Backup der MIZDB Datenbank" | sudo crontab -u root -
```

(Optional) Docker Images löschen:

```shell
docker image prune -a
```

## (optional) Docker deinstallieren

[https://docs.docker.com/engine/install/debian/#uninstall-docker-engine](https://docs.docker.com/engine/install/debian/#uninstall-docker-engine)
