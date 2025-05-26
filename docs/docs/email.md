E-Mail Benachrichtigungen einrichten
=======

Es können von MIZDB E-Mails an die Admins versendet werden; z.B. wenn Benutzer Feedback abgeben oder wenn ein Server
Error eingetreten ist.
Um E-Mail Benachrichtigungen einzurichten, müssen eine Reihe von zusätzlichen Angaben in die Datei `settings.py` im
MIZDB Grundverzeichnis eingetragen werden.

[comment]: <> (@formatter:off)  
!!! info "Verwendung `settings.py`"
    Die zusätzlichen Einstellungen können ab dieser Zeile eingetragen werden: 
    ```python
        # -----------------------------------------------------------------------------
        # Add your own settings here:
    ```

[comment]: <> (@formatter:on)

## 1. Admins registrieren

Unter dem Punkt `ADMINS` werden die Admins, die benachrichtigt werden sollen, mit Namen und E-MAil Adresse in eine Liste
eingetragen.

Zum Beispiel:

```python
ADMINS = [
    ("Admin", "admin@mail.com"),
    ("Willi Weber", "weber@web.de"),
    # weitere Admins...
]
```

## 2. Verbindungsdaten angeben

Als Nächstes müssen die Verbindungsdaten für den SMTP-Server eingetragen werden:

| SETTING             | Beschreibung                                                          |
|---------------------|-----------------------------------------------------------------------|
| EMAIL_HOST          | Der SMTP Server, mit dem die Mails verschickt werden.                 |
| EMAIL_PORT          | Port für den SMTP Server.                                             |
| EMAIL_HOST_USER     | Benutzername für den SMTP Server.                                     |
| EMAIL_HOST_PASSWORD | Benutzerpassword für den Server.                                      |
| SERVER_EMAIL        | Die Adresse, mit der die Mails für Fehlermeldungen verschickt werden. |

Zum Beispiel:

```python
EMAIL_HOST = "smtp.ionos.de"
EMAIL_PORT = 465
EMAIL_HOST_USER = "admin@mail.de"
EMAIL_HOST_PASSWORD = "mysupersecretpassword"
EMAIL_USE_SSL = True
SERVER_EMAIL = "admin@mail.de"
```

[comment]: <> (@formatter:off)  
!!! tip "Nützliche Links:"
    - [Django Settings für E-Mail](https://docs.djangoproject.com/en/5.2/ref/settings/#email-host)
    - [SMTP Serverdaten IONOS](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/)
    - [E-Mails mit Gmail-SMTP Server senden](https://support.google.com/a/answer/176600?hl=de)
    - [Blog Post: Sending emails with Django and Gmail](https://dev.to/abderrahmanemustapha/how-to-send-email-with-django-and-gmail-in-production-the-right-way-24ab)

[comment]: <> (@formatter:on)

---

Eine vollständige `settings.py` könnte also so aussehen:

```python
"""
Add your own settings that override the default settings.

For a list of settings, see:
    - https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from MIZDB.settings.defaults import BASE_DIR, secrets  # noqa
from MIZDB.settings.production import *  # noqa

# -----------------------------------------------------------------------------
# Add your own settings here:

ADMINS = [
    ("Admin", "admin@mail.com"),
    ("Willi Weber", "weber@web.de"),
]

EMAIL_HOST = "smtp.ionos.de"
EMAIL_PORT = 465
EMAIL_HOST_USER = "admin@mail.de"
EMAIL_HOST_PASSWORD = "mysupersecretpassword"
EMAIL_USE_SSL = True
SERVER_EMAIL = "admin@mail.de"
```

## 3. Docker Container/Apache neu starten

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

## 4. E-Mail Einstellungen testen

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

---

Oder zum Ausführen mit dem Python Interpreter der MIZDB Umgebung:

```python
import os

import django

os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
django.setup()


def send_admin_mail():
    from django.core.mail import mail_admins
    mail_admins("Test Admin Mail", "Test successful!")


if __name__ == "__main__":
    send_admin_mail()
```
