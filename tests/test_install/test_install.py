import unittest
from contextlib import contextmanager
from unittest import mock
from unittest.mock import mock_open

import install


class TestFuncs(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.mprint = mock.Mock()
        self.print_patch = mock.patch('install.print', new=self.mprint)
        self.print_patch.start()

    def tearDown(self):
        self.print_patch.stop()
        super().tearDown()

    def assertCMDCalled(self, cmd: str, calls: list):
        self.assertIn(cmd, [call.args[0] for call in calls])

    @mock.patch('install.run')
    def test_run_raises_InstallationAborted(self, run):
        for raise_on_error in (True, False):
            with self.subTest(raise_on_error=raise_on_error):
                run.return_value = mock.Mock(returncode=1, stderr=b'Woops')
                if not raise_on_error:
                    install._run(
                        'echo Hello, World',
                        raise_on_error=raise_on_error
                    )
                    self.assertEqual(
                        self.mprint.call_args_list[-2:],
                        [(('WARNUNG:',),), (('Woops',),)]
                    )
                else:
                    with self.assertRaises(install.InstallationAborted) as cm:
                        install._run(
                            'echo Hello, World',
                            raise_on_error=raise_on_error
                        )
                        self.assertEqual(cm.exception.args[0], 'Woops')

    def test_confirm_prompt_interrupt(self):
        """Check that the user can get out of the confirmation prompt."""
        with mock.patch('install.input') as mocked_input:
            mocked_input.side_effect = KeyboardInterrupt()
            with self.assertRaises(install.InstallationAborted):
                install.confirm("Have pizza?")

    def test_password_prompt_interrupted(self):
        """Check that the user can get out of the password prompt."""
        with mock.patch('install.getpass.getpass') as mocked_prompt:
            mocked_prompt.side_effect = KeyboardInterrupt()
            with self.assertRaises(install.InstallationAborted):
                install.password_prompt()

    @mock.patch('install._run')
    def test_install_system_packages(self, run):
        run.return_value = mock.Mock(returncode=0)
        install.install_system_packages()
        self.assertCMDCalled("sudo apt update", run.call_args_list)
        self.assertTrue(
            any(call.args[0].startswith("sudo apt install") for call in run.call_args_list),
            msg=f'Command "sudo apt install" not found in call args list:\n{run.call_args_list}'
        )

    @mock.patch('install.confirm')
    @mock.patch('install.run')
    def test_checks_postgres_server_version(self, run, confirm):
        """Check that the _server_ version of postgres is checked."""
        # String returned by the query to psql:
        show_sever_version = (
            '          server_version          \n----------------------------------\n 13.5 '
            '(Ubuntu 13.5-2.pgdg20.04+1)\n(1 Zeile)\n\n'
        )
        run.return_value = mock.Mock(
            returncode=0, stdout=show_sever_version.encode()
        )
        # version requirements are met
        with mock.patch('install.MIN_POSTGRES_VERSION', new=1):
            self.assertTrue(install.check_postgres_server(port=1))
        # version requirements are not met
        with mock.patch('install.MIN_POSTGRES_VERSION', new=15):
            for proceed_anyway in (True, False):
                with self.subTest(proceed_anyway=proceed_anyway):
                    confirm.return_value = proceed_anyway
                    if proceed_anyway:
                        self.assertFalse(install.check_postgres_server(port=1))
                    else:
                        with self.assertRaises(install.InstallationAborted):
                            install.check_postgres_server(port=1)

    @mock.patch('install.confirm')
    @mock.patch('install.run')
    def test_checks_postgres_server_version_unexpected_string(self, run, confirm):
        """
        check_postgres_server should catch exceptions raised from an unexpected
        string.
        """
        # "X" would raise an IndexError.
        # "don't make this crash" would raise a ValueError.
        for query_string in ("X", "don't make this crash"):
            with self.subTest(query_string=query_string):
                run.return_value = mock.Mock(
                    returncode=0, stdout=query_string.encode()
                )
                for proceed_anyway in (True, False):
                    with self.subTest(proceed_anyway=proceed_anyway):
                        confirm.return_value = proceed_anyway
                        if proceed_anyway:
                            try:
                                can_migrate = install.check_postgres_server(port=1)
                            except (IndexError, ValueError):
                                self.fail(
                                    "check_postgres_server couldn't handle an unexpected string"
                                )
                            self.assertFalse(can_migrate)
                        else:
                            with self.assertRaises(install.InstallationAborted):
                                install.check_postgres_server(port=1)

    @mock.patch('install.check_postgres_server')
    @mock.patch('install._run')
    def test_create_database(self, run, version_check):
        run.return_value = mock.Mock(returncode=0)
        version_check.return_value = True
        db_password = "'test_password'"  # a quoted string is expected
        port = 1
        db_name = "test_db"
        db_user = "test_user"
        can_migrate = install.create_database(
            port=port, db_name=db_name, db_user=db_user, db_password=db_password
        )
        self.assertCMDCalled(
            'sudo -u postgres psql -c '
            f'"CREATE USER {db_user} CREATEDB ENCRYPTED PASSWORD {db_password};"',
            run.call_args_list
        )
        self.assertCMDCalled(
            f'sudo -u postgres createdb {db_name} --owner={db_user}',
            run.call_args_list
        )
        self.assertTrue(can_migrate)

    @mock.patch('install.check_postgres_server')
    @mock.patch('install._run')
    def test_create_database_version_check_failed(self, run, version_check):
        run.return_value = mock.Mock(returncode=0)
        version_check.return_value = False
        can_migrate = install.create_database(
            port=1, db_name="db_name", db_user="db_user", db_password=""
        )
        self.assertFalse(can_migrate)

    @mock.patch('install.check_postgres_server')
    @mock.patch('install._run')
    def test_create_database_create_db_failed(self, run, version_check):
        run.return_value = mock.Mock(returncode=1)
        version_check.return_value = True
        can_migrate = install.create_database(
            port=1, db_name="db_name", db_user="db_user", db_password=""
        )
        self.assertFalse(can_migrate)

    @mock.patch('install.confirm')
    @mock.patch('install._run')
    def test_create_venv_exists(self, run, confirm):
        """
        create_venv should return early if the venv already exists and the user
        doesn't want to overwrite it.
        """
        run.return_value = mock.Mock(returncode=0)
        venv_directory = "~/.venv/archiv"
        with mock.patch('install.os.path.exists', new=mock.Mock(return_value=True)):
            for overwrite in (False, True):
                confirm.return_value = overwrite
                with self.subTest(overwrite=overwrite):
                    install.create_venv(venv_directory)
                    if overwrite:
                        run.assert_called()
                        self.assertCMDCalled(
                            f"python3 -m venv {venv_directory}", run.call_args_list
                        )
                        self.assertCMDCalled(
                            f"{venv_directory}/bin/pip install -qU pip", run.call_args_list
                        )
                    else:
                        run.assert_not_called()

    @mock.patch('install._run')
    def test_install_python_packages(self, run):
        run.return_value = mock.Mock(returncode=0)
        venv_directory = "~/.venv/archiv"
        project_directory = "~/archiv/MIZDB"
        install.install_python_packages(
            venv_directory=venv_directory,
            project_directory=project_directory
        )
        self.assertCMDCalled(
            f"{venv_directory}/bin/pip install -qr {project_directory}/requirements.txt",
            run.call_args_list
        )

    @mock.patch('install._run')
    def test_create_config(self, run):
        venv_directory = "~/.venv/archiv"
        project_directory = "~/stuff/MIZDB"
        with mock.patch('install.open', mock_open()) as mocked_open:
            handle = mocked_open.return_value
            run.return_value = mock.Mock(returncode=0, stdout=b"supersecret")
            success = install.create_config(
                venv_directory=venv_directory,
                project_directory=project_directory,
                port="1234",
                host="notlocalhost",
                db_name="mizdb",
                db_user="mizdb",
                db_password="'hunter2'"  # a quoted string is expected
            )
        self.assertCMDCalled(
            f"{venv_directory}/bin/python3 -c "
            '"from django.core.management import utils; print(utils.get_random_secret_key())"',
            run.call_args_list
        )
        self.assertEqual((f"{project_directory}/config.yaml", 'w'), mocked_open.call_args[0])
        handle.write.assert_called()
        config = handle.write.call_args[0][0]
        self.assertIn("SECRET_KEY: 'supersecret'", config)
        self.assertIn("ALLOWED_HOSTS: ['notlocalhost']", config)
        self.assertIn("DATABASE_USER: 'mizdb'", config)
        self.assertIn("DATABASE_PASSWORD: 'hunter2'", config)
        self.assertIn("DATABASE_NAME: 'mizdb'", config)
        self.assertIn("DATABASE_HOST: 'localhost'", config)
        self.assertIn("DATABASE_PORT: '1234'", config)
        self.assertIn("WIKI_URL: 'http://notlocalhost/wiki/Hauptseite'", config)
        self.assertTrue(success)

    @mock.patch('install._run')
    def test_create_config_no_secret_key(self, run):
        """
        create_config should return False, if no secret key could be generated.
        """
        with mock.patch('install.open'):
            run.return_value = mock.Mock(returncode=1, stdout=b"")
            success = install.create_config(
                venv_directory="~/.venv/archiv",
                project_directory="~/projects/MIZDB",
                port="1234",
                host="notlocalhost",
                db_name="mizdb",
                db_user="mizdb",
                db_password="'hunter2'"  # a quoted string is expected
            )
            self.assertFalse(success)

    @mock.patch('install._run')
    def test_install_mod_wsgi(self, run):
        venv_directory = "~/tests"
        run.return_value = mock.Mock(returncode=0)
        with mock.patch('install.open', mock_open()) as mocked_open:
            handle = mocked_open.return_value
            install.install_mod_wsgi(
                venv_directory=venv_directory, project_directory=venv_directory, host="google.com"
            )
            self.assertCMDCalled(
                f"{venv_directory}/bin/pip install -q mod_wsgi", run.call_args_list
            )
            # Check the mod_wsgi module loader:
            self.assertCMDCalled(
                f"sudo {venv_directory}/bin/mod_wsgi-express install-module",
                run.call_args_list
            )
            self.assertIn((('mod_wsgi.load', 'w'),), mocked_open.call_args_list)
            handle.write.assert_called()
            self.assertCMDCalled(
                "sudo mv mod_wsgi.load /etc/apache2/mods-available/mod_wsgi.load",
                run.call_args_list
            )
            self.assertCMDCalled("sudo a2enmod -q mod_wsgi macro", run.call_args_list)
            # Check the site config:
            self.assertIn((('mizdb.conf', 'w'),), mocked_open.call_args_list)
            self.assertCMDCalled(
                "sudo mv mizdb.conf /etc/apache2/sites-available/mizdb.conf",
                run.call_args_list
            )
            self.assertCMDCalled("sudo a2ensite -q mizdb", run.call_args_list)
            self.assertCMDCalled("sudo -k service apache2 restart", run.call_args_list)


class TestInstall(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.mprint = mock.Mock()
        self.print_patch = mock.patch('install.print', new=self.mprint)
        self.print_patch.start()
        # Prepare mocks for the functions used in the installation process:
        self._run = mock.Mock()
        self.confirm = mock.Mock()
        self.cwd = mock.Mock()
        self.create_config = mock.Mock()
        self.create_database = mock.Mock()
        self.create_venv = mock.Mock()
        self.install_mod_wsgi = mock.Mock()
        self.install_python_packages = mock.Mock()
        self.install_system_packages = mock.Mock()
        self.open = mock.Mock()
        self.password_prompt = mock.Mock()

    def tearDown(self):
        self.print_patch.stop()
        super().tearDown()

    @contextmanager
    def patch(self, *exclude):
        patches = []
        to_patch = [
            'install.confirm',
            'install._run',
            'install.password_prompt',
            'install.install_system_packages',
            'install.create_database',
            'install.create_venv',
            'install.install_python_packages',
            'install.create_config',
            'install.install_mod_wsgi',
            'install.Path.cwd',
            'install.open',
        ]
        for attr in to_patch:
            if attr in exclude:
                continue
            # Use the mocks prepared in setUp():
            patch = mock.patch(attr, new=getattr(self, attr.rsplit('.', 1)[-1]))
            patches.append(patch)
            patch.start()
        yield
        for patch in patches:
            patch.stop()

    # noinspection PyMethodMayBeStatic
    def get_install_kwargs(self, **kwargs):
        return {
            'venv_directory': "~/.venv",
            'port': "5432",
            'host': "localhost",
            'db_name': "mizdb",
            'db_user': "mizdb",
            **kwargs
        }

    def test_install(self):
        with self.patch():
            install.install(**self.get_install_kwargs())
            self.install_system_packages.assert_called()
            self.create_database.assert_called()
            self.create_venv.assert_called()
            self.install_python_packages.assert_called()
            self.create_config.assert_called()
            self.install_mod_wsgi.assert_called()

    def test_install_venv_directory(self):
        """
        venv_directory should point at a subdirectory of the project directory,
        if venv_directory parameter was not supplied.
        """
        with self.patch():
            self.cwd = "~/projects/MIZDB"
            install.install(**self.get_install_kwargs(venv_directory=""))
            self.create_venv.called_with("~/projects/MIZDB/.venv/archiv")
            install.install(**self.get_install_kwargs(venv_directory="woop"))
            self.create_venv.called_with("woop")

    def test_skip_migrations(self):
        """
        install should not apply migrations, if create_database 'failed' or if
        the config file could not be generated.
        """
        with self.patch():
            project_directory = self.cwd = "."
            venv_directory = "~"
            # No database:
            self.create_config.return_value = True
            self.create_database.return_value = False
            install.install(**self.get_install_kwargs(venv_directory=venv_directory))
            self.assertNotIn(
                f"{venv_directory}/bin/python3 {project_directory}/manage.py migrate",
                [call.args for call in self._run.call_args_list]
            )
            # No config:
            self.create_config.return_value = False
            self.create_database.return_value = True
            install.install(**self.get_install_kwargs(venv_directory=venv_directory))
            self.assertNotIn(
                f"{venv_directory}/bin/python3 {project_directory}/manage.py migrate",
                [call.args for call in self._run.call_args_list]
            )


if __name__ == '__main__':
    unittest.main()
