E-Mail Benachrichtigungen einrichten
=======

Um bei Server Fehlern automatisch Benachrichtigungen an Admins zu schicken, müssen eine Reihe von zusätzlichen Angaben
gemacht
werden.

## 1. Admins einrichten

In der `ADMINS` Datei werden die Admins eingetragen, die benachrichtigt werden sollen. Diese Datei befindet sich im
Grundverzeichnis der Anwendung, dem MIZDB Ordner (dort wo auch Dateien wie `mizdb.sh` und `manage.py` zu finden sind).
Ist die Datei noch nicht vorhanden, muss sie erstellt werden, z.B.: `touch /pfad/zu/MIZDB/ADMINS`.

Für jeden Admin muss dabei eine neue Zeile mit Name und E-Mail-Adresse angelegt werden. Zeilen, die mit `#` beginnen,
werden ignoriert:

```text
# name, email address
Admin, admin@mail.com
Willi Weber, weber@web.de
```

## 2. Verbindungsdaten angeben

Abgesehen vom Passwort für den E-Mailbenutzer, werden die Verbindungsdaten für den E-Mail-Server als Umgebungsvariablen
an die Einstellungen der Anwendung übergeben. Dazu werden die notwendigen Daten in die Datei `.env` (ebenfalls im MIZDB
Grundverzeichnis) eingetragen.

Notwendige Daten:

| SETTING             | Beschreibung                                          |
|---------------------|-------------------------------------------------------|
| EMAIL_HOST          | Der SMTP Server, mit dem die Mails verschickt werden. |
| EMAIL_PORT          | Port für den SMTP Server.                             |
| EMAIL_HOST_USER     | Benutzername für den SMTP Server.                     |
| EMAIL_HOST_PASSWORD | Benutzerpassword für den Server.                      |

Zusätzliche Einstellungen sind `EMAIL_USE_TLS` und `EMAIL_USE_SSL`, die beschreiben, ob bei der Kommunikation mit dem
SMTP Server TLS oder SSL benutzt werden soll. Die einzutragenden Werte müssen hier `true` oder `false` sein, und nur
einer der Werte darf `true` sein.

Außerdem kann mit `SERVER_EMAIL` die E-Mail-Adresse festgelegt werden, von
der E-Mails bezüglich Fehlermeldungen verschickt werden. Wird kein Wert angegeben, werden die E-Mails von
`EMAIL_HOST_USER` versendet.

Beispiel, Auszug aus der `.env` Datei:

```yaml
# ...

# Settings for sending e-mail
EMAIL_HOST = smtp.ionos.de
EMAIL_PORT = 465
EMAIL_HOST_USER = myuser@mail.com
EMAIL_USE_SSL = true
```

[comment]: <> (@formatter:off)  
!!! tip "Nützliche Links:"
    - [Django Settings für E-Mail](https://docs.djangoproject.com/en/5.2/ref/settings/#email-host)
    - [SMTP Serverdaten IONOS](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/)
    - [E-Mails mit Gmail-SMTP Server senden](https://support.google.com/a/answer/176600?hl=de)
    - [Blog Post: Sending emails with Django and Gmail](https://dev.to/abderrahmanemustapha/how-to-send-email-with-django-and-gmail-in-production-the-right-way-24ab)

[comment]: <> (@formatter:on)

## 3. E-Mail Password ablegen

Das Passwort für den Benutzer des E-Mail-Servers muss in die Datei `.secrets` eingetragen werden. Die Datei ist
ebenfalls im MIZDB Grundverzeichnis zu finden.

```yaml
# ...

EMAIL_HOST_PASSWORD: "mysupersecretpassword"
```

[comment]: <> (@formatter:off)  
!!! warning "Achtung: Die Syntax in der `.secrets` Datei ist unterschiedlich zu der in der `.env` Datei!"  
  
[comment]: <> (@formatter:on)

## 4. Docker Container/Apache neu starten

Abschließend muss der Docker Container der Anwendung neu gestartet werden, um die Änderungen anzuwenden:

### Docker

```shell
mizdb restart
```

### Ohne Docker

Oder, wenn ohne Docker installiert wurde, Apache neu laden:

```shell
sudo service apache2 reload
```

## 5. E-Mail Einstellungen testen

### Systemcheck

Es kann ein Systemcheck durchgeführt werden, um zu prüfen, dass die Angaben und ihre Formatierung korrekt
sind:

#### Docker

Bei einer Installation mit Docker:

```shell
mizdb check
```

#### Ohne Docker

Oder bei einer Installation ohne Docker, diese Zeile im MIZDB Grundverzeichnis ausführen:

```shell
DJANGO_SETTINGS_MODULE=MIZDB.settings .venv/bin/python3 manage.py check
```

### Test-Mail versenden

Zu Testzwecken kann man mit Django auch direkt eine Mail an die Admins verschicken, siehe die Django Dokumentation für
die
Funktion [mail_admins](https://docs.djangoproject.com/en/5.2/topics/email/#mail-admins).

Bei einer Docker Installation zunächst in den Container wechseln:

```shell
mizdb shell
```

Anschließend:

```shell
python manage.py shell -c 'from django.core.mail import mail_admins; mail_admins("Test Admin Mail", "Test successful!")'
```

Oder zum Ausführen mit dem Python Interpreter der MIZDB Umgebung:

```python
import os

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "MIZDB.settings"
django.setup()


def send_admin_mail():
    from django.core.mail import mail_admins
    mail_admins("Test Admin Mail", "Test successful!")


if __name__ == "__main__":
    send_admin_mail()
```
