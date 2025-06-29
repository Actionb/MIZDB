from django.core.management.base import BaseCommand
from pathlib import Path

import requests
from semver import Version

# PROJECT_ROOT is the fourth parent: PROJECT_ROOT/dbentry/management/commands
LOCAL_VERSION_PATH = Path(__file__).parents[3].joinpath("VERSION")
REMOTE_VERSION_URL = "https://raw.githubusercontent.com/Actionb/MIZDB/refs/heads/master/VERSION"


class UpdateCheckFailed(Exception):
    pass


def _get_local_version():
    """
    Return the local version string of the MIZDB app.

    The local version is stored in the VERSION file in the project root.

    Raises an UpdateCheckFailed exception if the VERSION files does not exist or
    if it could not be read, or if the local version is not a valid semver.
    """
    try:
        with open(LOCAL_VERSION_PATH, "r") as f:
            local = f.read().strip()
    except FileNotFoundError:
        raise UpdateCheckFailed(f"Versions Datei konnte nicht gefunden werden. (Pfad: {LOCAL_VERSION_PATH})")
    except PermissionError:
        raise UpdateCheckFailed(f"Versions Datei konnte nicht gelesen werden. (Pfad: {LOCAL_VERSION_PATH})")
    try:
        return Version.parse(local)
    except ValueError:
        raise UpdateCheckFailed(f"Lokale Version ist keine gültige Versionsnummer. (Version: {LOCAL_VERSION_PATH})")


def _get_remote_version():
    """
    Return the latest version string of the MIZDB app in the GitHub repo.

    Raises an UpdateCheckFailed exception if the response was not ok or if the
    remote version is not a valid semver.
    """
    response = requests.get(url="https://raw.githubusercontent.com/Actionb/MIZDB/refs/heads/master/VERSION")
    if not response.ok:
        raise UpdateCheckFailed(f"Failed to fetch remote version: {response.status_code}")
    remote = response.content.decode()
    try:
        return Version.parse(remote)
    except ValueError:
        raise UpdateCheckFailed(f"Remote Version ist keine gültige Versionsnummer. (Version: {remote})")


def update_available():
    try:
        remote = _get_remote_version()
        local = _get_local_version()
    except UpdateCheckFailed as e:
        print(f"Fehler: {str(e)}")
        exit(1)
    return Version.compare(remote, local) > 0, remote, local


class Command(BaseCommand):
    help = "Check if an update for the MIZDB app is available"

    def handle(self, *args, **options):
        _update_available, remote_version, local_version = update_available()
        if _update_available:
            print(f"Ein Update ist verfügbar: Version '{local_version}' -> '{remote_version}'")
            exit(0)
        else:
            print(f"Bereits aktuell: Version '{local_version}'")
            exit(1)
