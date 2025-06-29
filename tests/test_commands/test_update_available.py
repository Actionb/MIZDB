from unittest.mock import patch, mock_open, Mock, DEFAULT

import requests_mock
from semver import Version

from tests.case import MIZTestCase

from dbentry.management.commands.update_available import (
    _get_local_version,
    UpdateCheckFailed,
    REMOTE_VERSION_URL,
    _get_remote_version,
    update_available,
    Command,
)


class TestUpdateAvailable(MIZTestCase):
    def test_get_local_version(self):
        """
        Assert that _get_local_version returns a Version object with the local
        version.
        """
        with patch("dbentry.management.commands.update_available.open", mock_open(read_data="0.0.1")):
            local = _get_local_version()
            self.assertIsInstance(local, Version)
            self.assertEqual(str(local), "0.0.1")

    def test_get_local_version_file_not_found(self):
        """
        Assert that _get_local_version raises a UpdateCheckFailed exception
        when the VERSION file does not exist.
        """
        with patch("dbentry.management.commands.update_available.open", new=Mock(side_effect=FileNotFoundError)):
            self.assertRaises(UpdateCheckFailed, _get_local_version)

    def test_get_local_version_file_cannot_be_read(self):
        """
        Assert that _get_local_version raises a UpdateCheckFailed exception
        when the VERSION file could not be read.
        """
        with patch("dbentry.management.commands.update_available.open", new=Mock(side_effect=PermissionError)):
            self.assertRaises(UpdateCheckFailed, _get_local_version)

    def test_get_local_version_invalid_semver(self):
        """
        Assert that _get_local_version raises a UpdateCheckFailed exception
        when the local version is not a valid semver.
        """
        with patch("dbentry.management.commands.update_available.open", mock_open(read_data="foo")):
            self.assertRaises(UpdateCheckFailed, _get_local_version)

    def test_get_remote_version(self):
        """
        Assert that _get_remote_version returns a Version object with the
        remote version.
        """
        with requests_mock.Mocker() as m:
            m.get(REMOTE_VERSION_URL, text="0.0.1")
            remote = _get_remote_version()
            self.assertIsInstance(remote, Version)
            self.assertEqual(str(remote), "0.0.1")

    def test_get_remote_version_response_not_ok(self):
        """
        Assert that _get_remote_version raises a UpdateCheckFailed exception
        when the request for the remote version did not return a response with
        an OK status code.
        """
        with requests_mock.Mocker() as m:
            m.get(REMOTE_VERSION_URL, status_code=400)
            self.assertRaises(UpdateCheckFailed, _get_remote_version)

    def test_get_remote_version_invalid_semver(self):
        """
        Assert that _get_remote_version raises a UpdateCheckFailed exception
        when the remote version is not a valid semver.
        """
        with requests_mock.Mocker() as m:
            m.get(REMOTE_VERSION_URL, text="foo")
            self.assertRaises(UpdateCheckFailed, _get_remote_version)

    def test_update_available(self):
        """
        Assert that update_available returns True if remote version > local
        version.
        """
        test_data = [
            # local, remote, expected return value for update_available
            ("0.0.1", "0.0.1", False),
            ("0.0.1", "0.0.2", True),
            ("0.0.2", "0.0.1", False),
        ]
        for local, remote, expected in test_data:
            with self.subTest(local=local, remote=remote):
                with patch("dbentry.management.commands.update_available.open", mock_open(read_data=local)):
                    with requests_mock.Mocker() as m:
                        m.get(REMOTE_VERSION_URL, text=remote)
                        self.assertEqual(update_available(), (expected, remote, local))

    @patch.multiple(
        "dbentry.management.commands.update_available",
        _get_local_version=DEFAULT,
        _get_remote_version=DEFAULT,
        print=DEFAULT,
    )
    def test_update_available_exits_on_local_version_exception(self, _get_local_version, **_mocks):
        """
        Assert that update_available exits with status code 1 if
        _get_local_version raises an UpdateCheckFailed exception.
        """
        _get_local_version.side_effect = UpdateCheckFailed("Testing Errors")
        with self.assertRaises(SystemExit) as cm:
            update_available()
            self.assertEqual(cm.exception.code, 1)

    @patch.multiple(
        "dbentry.management.commands.update_available",
        _get_local_version=DEFAULT,
        _get_remote_version=DEFAULT,
        print=DEFAULT,
    )
    def test_update_available_exits_on_remote_version_exception(self, _get_remote_version, **_mocks):
        """
        Assert that update_available exits with status code 1 if
        _get_remote_version raises an UpdateCheckFailed exception.
        """
        _get_remote_version.side_effect = UpdateCheckFailed
        with self.assertRaises(SystemExit) as cm:
            update_available()
        self.assertEqual(cm.exception.code, 1)

    @patch("dbentry.management.commands.update_available.print")
    def test_handle(self, _print_mock):
        """Assert that handle exits with status code 0 if an update is available."""
        with patch("dbentry.management.commands.update_available.open", mock_open(read_data="0.0.1")):
            with requests_mock.Mocker() as m:
                m.get(REMOTE_VERSION_URL, text="0.0.2")
                with self.assertRaises(SystemExit) as cm:
                    Command().handle()
                self.assertEqual(cm.exception.code, 0)

    @patch("dbentry.management.commands.update_available.print")
    def test_handle_no_update(self, _print_mock):
        """Assert that handle exits with status code 1 if no update is available."""
        with patch("dbentry.management.commands.update_available.open", mock_open(read_data="0.0.1")):
            with requests_mock.Mocker() as m:
                m.get(REMOTE_VERSION_URL, text="0.0.1")
                with self.assertRaises(SystemExit) as cm:
                    Command().handle()
                self.assertEqual(cm.exception.code, 1)
