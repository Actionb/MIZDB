#!/usr/bin/env python3
"""
Compare the version numbers of the current local git tag and the latest git tag
of the remote.

Exits with code 0 if an update is available. Exits with code 1 if no update is
available.
"""

from pathlib import Path

import requests
import semver

API_URL = "https://api.github.com/repos/Actionb/MIZDB/tags"


def _get_current_version() -> str:
    """Return the current version string of the MIZDB app."""
    with open(Path(__file__).parent.parent.joinpath("VERSION"), "r") as f:
        return f.read().strip()


def _get_remote_version() -> str:
    """Return the latest version string of the MIZDB app in the GitHub repo."""
    response = requests.get(
        url=API_URL,
        headers={"Accept": "application/vnd.github+json", "X-Github-Api-Version": "2022-11-28"},
    )
    if response.ok:
        return response.json()[0]["name"]
    else:
        # TODO: emit an error message
        return "0.0.0"


def update_available():
    """Return whether an update is available from the repo."""
    return semver.compare(_get_remote_version(), _get_current_version()) > 0


if __name__ == "__main__":
    # Invert the return values to exit with expected appropriate exit code:
    exit(bool(not update_available()))
