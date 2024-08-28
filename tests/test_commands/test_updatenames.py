import io
from unittest.mock import Mock, patch

from django.test import TestCase

from dbentry.management.commands.updatenames import Command

from .models import UpdateCNModel, UpdateNormalModel

models_list_mock = Mock(return_value=[UpdateCNModel, UpdateNormalModel])


@patch("dbentry.management.commands.updatenames.apps.get_models", new=models_list_mock)
class TestCommand(TestCase):
    @patch("dbentry.query.CNQuerySet._update_names")
    def test_handle(self, update_names_mock):
        """Assert that handle calls _update_names on ComputedNameModels."""
        cmd = Command(stdout=io.StringIO())
        cmd.handle(force=False)
        update_names_mock.assert_called()

    @patch("dbentry.query.CNQuerySet.update")
    def test_handle_force_option(self, update_mock):
        """
        Assert that an update is forced on ComputedNameModels if using
        force=True as option.
        """
        cmd = Command(stdout=io.StringIO())
        cmd.handle(force=True)
        update_mock.assert_called_with(_changed_flag=True)
