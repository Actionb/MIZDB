FROM python:3.11-alpine AS build

RUN ["apk", "update"]
RUN ["apk", "add", "build-base", "apache2-dev", "git"]

# Set up uv for Docker:
# https://docs.astral.sh/uv/guides/integration/docker/
COPY --from=ghcr.io/astral-sh/uv:0.3.4 /uv /bin/uv
RUN uv venv /opt/venv
ENV VIRTUAL_ENV=/opt/venv

# Temporarily mount the requirements:
# https://docs.docker.com/build/building/best-practices/#add-or-copy
RUN --mount=type=bind,source=requirements,target=/tmp/requirements ["uv", "pip", "install", "-r", "/tmp/requirements/base.txt"]

FROM python:3.11-alpine AS final

# Don't run your app as root.
RUN addgroup --system app
RUN adduser --system --ingroup app --no-create-home app

RUN ["apk", "update", "&&", "upgrade"]
# libpq required by psycopg2
RUN ["apk", "add", "libpq", "apache2"]

COPY --from=build --chown=app:app /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

USER app
WORKDIR /mizdb
COPY . /mizdb
EXPOSE 80
