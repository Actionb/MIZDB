import json
import re
import subprocess

import semver

API_URL = "https://api.github.com/repos/Actionb/MIZDB/tags"


def _get_current_version() -> str:
    """Return the current version string of the MIZDB app."""
    current_tag = subprocess.run(["git", "describe"], capture_output=True).stdout.decode("utf-8")
    pattern = re.compile(r"^(\d+\.\d+.\d+)?.*")
    return pattern.match(current_tag).group(1)


def _get_remote_version() -> str:
    """Return the latest version string of the MIZDB app in the GitHub repo."""
    command = f'curl -L -H "Accept: application/vnd.github+json" -H "X-Github-Api-Version: 2022-11-28" {API_URL}'
    remote_tags = json.loads(subprocess.run(command.split(" "), capture_output=True).stdout.decode("utf-8"))
    return remote_tags[0]["name"]


def update_available():
    """Return whether an update is available from the repo."""
    return semver.compare(_get_remote_version(), _get_current_version()) > 0


if __name__ == "__main__":
    if update_available():
        exit(0)
    else:
        exit(1)
