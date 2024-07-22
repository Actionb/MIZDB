Deinstallation
=======

```shell
# Docker Container anhalten:
docker stop mizdb-app mizdb-postgres
# MIZDB Verzeichnis löschen:
sudo rm -rf <PFAD/ZUM/MIZDB_VERZEICHNIS>
# Management-Skript löschen:
sudo rm -f /usr/local/bin/mizdb
```

(Optional) Docker Images löschen:

```shell
docker image prune -a
```

Docker deinstallieren: 
[https://docs.docker.com/engine/install/debian/#uninstall-docker-engine](https://docs.docker.com/engine/install/debian/#uninstall-docker-engine)
