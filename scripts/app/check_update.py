#!/usr/bin/env python3
"""
Check if an update is available.

Compares the version numbers of the current local git tag and the latest git
tag of the remote.

Exits with code 0 if an update is available. Exits with code 1 if no update is
available.

Note that this is expected to run inside the Docker container.
"""

from pathlib import Path

import requests
import semver

API_URL = "https://api.github.com/repos/Actionb/MIZDB/tags"
# Currently supported API versions:
# https://docs.github.com/de/rest/about-the-rest-api/api-versions?apiVersion=2022-11-28#supported-api-versions
API_VERSION = "2022-11-28"


class UpdateCheckFailed(Exception):
    pass


def _get_local_version() -> str:
    """
    Return the local version string of the MIZDB app.

    The local version is stored in the VERSION file in the project root.

    Raises an UpdateCheckFailed exception if the VERSION files does not exist or
    if it could not be read.
    """
    # PROJECT_ROOT is the third parent: PROJECT_ROOT/scripts/app/
    file_path = Path(__file__).parents[2].joinpath("VERSION")
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        raise UpdateCheckFailed(f"Versions Datei konnte nicht gefunden werden. (Pfad: {file_path})")
    except PermissionError:
        raise UpdateCheckFailed(f"Versions Datei konnte nicht gelesen werden. (Pfad: {file_path})")


def _get_remote_version() -> str:
    """
    Return the latest version string of the MIZDB app in the GitHub repo.

    Fetches the list of tags from the repo and returns the name of the latest
    one.

    Raises an UpdateCheckFailed exception if the API response was not ok.
    """
    response = requests.get(
        url=API_URL,
        headers={"Accept": "application/vnd.github+json", "X-Github-Api-Version": API_VERSION},
    )
    if response.ok:
        return response.json()[0]["name"]
    else:
        raise UpdateCheckFailed(f"Anfrage an GitHub fehlgeschlagen: (Status Code: {response.status_code})")


def check_for_update() -> tuple[bool, str, str]:
    """
    Return whether an update is available from the repo.

    Exits with status code 1 if an UpdateCheckFailed exception was raised.

    Returns a three tuple:
        - bool: whether the remote version is higher than the local version
        - str: remote version string
        - str: local version string
    """
    try:
        remote = _get_remote_version()
        local = _get_local_version()
    except UpdateCheckFailed as e:
        print(f"Fehler: {str(e)}")
        exit(1)
    return semver.compare(remote, local) > 0, remote, local


if __name__ == "__main__":
    update_available, remote_version, local_version = check_for_update()
    if update_available:
        print(f"Ein Update ist verfügbar: Version '{local_version}' -> '{remote_version}'")
        exit(0)
    else:
        print(f"Bereits aktuell: Version '{local_version}'")
        exit(1)
