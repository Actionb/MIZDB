Deinstallation
=======

## Container stoppen

Um MIZDB zu deinstallieren, sollten zunächst die Docker Container gestoppt und werden:

```shell
docker compose --env-file docker-compose.env down
```

## Volumen entfernen

Anschließend können auch die Volumes (falls verwendet) mit den Daten der Datenbank und den Logs entfernt werden:


[comment]: <> (@formatter:off)  
!!! danger "Die Daten aus der Datenbank werden dabei unwiederbringlich gelöscht!"
[comment]: <> (@formatter:on)

```shell
docker volume rm mizdb_{pgdata,logs}
```

[comment]: <> (@formatter:off)  
!!! note "Hinweis: COMPOSE_PROJECT_NAME"
    Der Präfix `mizdb` im Befehl oben entspricht dem Wert für `COMPOSE_PROJECT_NAME` in `docker-compose.env`.
[comment]: <> (@formatter:on)

## Images löschen

Die nun nicht mehr benötigten Images können auch gelöscht werden:

```shell
docker image prune
```

## Management Skript entfernen

Der `mizdb` Befehl kann auf diese Weise vom System entfernt werden:
```shell
rm ~/.local/bin/mizdb
```

## Backup Cronjob entfernen

Falls [cronjobs für Backups](verwaltung.md#backups-automatisieren) erstellt wurden, sollten diese entfernt werden:
```shell
sudo crontab -e
```
