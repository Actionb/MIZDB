FROM python:3.11-bookworm

RUN ["apt", "update"]
RUN ["apt", "install", "-y", "apache2", "apache2-dev"]
RUN ["python3", "-m", "pip", "install", "--upgrade", "pip", "wheel"]
# mod_wsgi attempts to set the locale to en-US.UTF-8, so make sure the locale is
# installed to eliminate a minor warning message.
RUN ["apt", "install", "-y", "locales"]
RUN ["localedef", "-i", "en_US", "-c", "-f", "UTF-8", "-A", "/usr/share/locale/locale.alias", "en_US.UTF-8"]

WORKDIR /mizdb
COPY requirements requirements
RUN ["python3", "-m", "pip", "install", "-r", "requirements/dev.txt"]
COPY . /mizdb
EXPOSE 80
