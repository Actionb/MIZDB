E-Mail Benachrichtigungen einrichten
=======

Es können von MIZDB E-Mails an die Admins versendet werden; z.B. wenn Benutzer Feedback abgeben oder wenn ein Server
Error eingetreten ist. Um E-Mail Benachrichtigungen einzurichten, müssen eine Reihe von zusätzlichen Angaben in
die [MIZDB Konfigurationsdatei](install.md#mizdb-konfigurieren) gemacht werden.

[comment]: <> (@formatter:off)  
!!! info "Wo finde ich die Konfigurationsdatei?"
    Der Befehl `mizdb config` zeigt den Pfad zu der Konfigurationsdatei an. 

[comment]: <> (@formatter:on)

## 1. Admins registrieren

Unter dem Punkt `ADMINS` werden die E-Mail-Adressen der Admins, die benachrichtigt werden sollen, eingetragen.

Zum Beispiel:

```dotenv
ADMINS=admin@mail.com,weber@web.de
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

```dotenv
EMAIL_HOST=smtp.ionos.de
EMAIL_PORT=465
EMAIL_HOST_USER=admin@mail.de
EMAIL_HOST_PASSWORD=mysupersecretpassword
EMAIL_USE_SSL=True
SERVER_EMAIL=admin@mail.de
```

[comment]: <> (@formatter:off)  
!!! tip "Nützliche Links:"
    - [Django Settings für E-Mail](https://docs.djangoproject.com/en/5.2/ref/settings/#email-host)
    - [SMTP Serverdaten IONOS](https://www.ionos.de/hilfe/e-mail/allgemeine-themen/serverinformationen-fuer-imap-pop3-und-smtp/)
    - [E-Mails mit Gmail-SMTP Server senden](https://support.google.com/a/answer/176600?hl=de)
    - [Blog Post: Sending emails with Django and Gmail](https://dev.to/abderrahmanemustapha/how-to-send-email-with-django-and-gmail-in-production-the-right-way-24ab)

[comment]: <> (@formatter:on)

---

## 3. Docker Container/Apache neu starten

Abschließend muss der Docker Container der Anwendung neu gestartet werden, um die Änderungen anzuwenden:

```shell
mizdb restart
```

## 4. E-Mail Einstellungen testen

### Systemcheck

Es kann ein Systemcheck durchgeführt werden, um zu prüfen, dass die Angaben und ihre Formatierung korrekt
sind:

Bei einer Installation mit Docker:

```shell
mizdb check
```

### Test-Mail versenden

Zu Testzwecken kann man mit Django auch direkt eine Mail an die Admins verschicken, siehe die Django Dokumentation für
die Funktion [mail_admins](https://docs.djangoproject.com/en/5.2/topics/email/#mail-admins).

Zunächst in den Container wechseln:

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
