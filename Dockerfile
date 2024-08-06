FROM python:3.11-alpine AS build

RUN ["apk", "update"]
RUN ["apk", "add", "build-base", "apache2-dev", "git"]
RUN ["python3", "-m", "pip", "install", "--upgrade", "pip", "wheel"]

WORKDIR /mizdb
COPY requirements requirements
RUN ["python3", "-m", "pip", "install", "-r", "requirements/base.txt"]

FROM python:3.11-alpine AS final

RUN ["apk", "update", "&&", "upgrade"]
# libpq required by psycopg2
RUN ["apk", "add", "libpq", "apache2"]

COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

WORKDIR /mizdb
# NOTE: check the dockerignore file to see which files and directories will be copied to the image
COPY . /mizdb
EXPOSE 80
