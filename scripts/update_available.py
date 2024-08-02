import re
import subprocess

import requests
import semver

API_URL = "https://api.github.com/repos/Actionb/MIZDB/tags"


def _get_current_version() -> str:
    """Return the current version string of the MIZDB app."""
    current_tag = subprocess.run(["git", "describe"], capture_output=True).stdout.decode("utf-8")
    pattern = re.compile(r"^(\d+\.\d+\.\d+)?.*")
    return pattern.match(current_tag).group(1)


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
    if update_available():
        exit(0)
    else:
        exit(1)
