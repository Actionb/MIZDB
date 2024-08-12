#!/usr/bin/env python3
"""Bump the semantic version number defined in the VERSION file."""
from argparse import ArgumentParser
from pathlib import Path

from semver import Version

VERSION_FILE_PATH = Path(__file__).parents[1].joinpath("VERSION")


def _get_version(version_file_path) -> Version:
    with open(version_file_path, "r") as f:
        return Version.parse(f.read())


def _bump_major(version: Version, file_path: Path) -> Version:
    return _write_version(version.bump_major(), file_path)


def _bump_minor(version: Version, file_path: Path) -> Version:
    return _write_version(version.bump_minor(), file_path)


def _bump_patch(version: Version, file_path: Path) -> Version:
    return _write_version(version.bump_patch(), file_path)


def _write_version(version: Version, file_path: Path) -> Version:
    with open(file_path, "w") as f:
        f.write(str(version))
    return version


def _bump(bump_type: str, file_path: Path):
    current_version = _get_version(file_path)

    if bump_type == "major":
        new_version = _bump_major(current_version, file_path)
    elif bump_type == "minor":
        new_version = _bump_minor(current_version, file_path)
    elif bump_type == "patch":
        new_version = _bump_patch(current_version, file_path)
    else:
        raise Exception("Unknown bump type")
    print(f"Bumped version to: '{new_version}'\nVERSION file: {file_path.absolute()}")


def bump(bump_type: str, file_path: Path):
    """Bump the version in the version file given by ``file_path``."""
    try:
        _bump(bump_type, file_path)
    except Exception as e:
        print(e)
        exit(1)


if __name__ == "__main__":
    parser = ArgumentParser(description="Bump the semantic version number defined in the VERSION file.")
    parser.add_argument("bump_type", choices=["major", "minor", "patch"], help="the type of version bump")
    parser.add_argument(
        "-f",
        "--file",
        help="path to the version file",
        type=Path,
        default=VERSION_FILE_PATH,
    )
    args = parser.parse_args()
    bump(args.bump_type, args.file)
