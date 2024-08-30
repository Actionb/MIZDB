from unittest.mock import Mock, patch

from django.db import models

from dbentry.site.views.export import BaseExportView, ExportActionView
from tests.case import ViewTestCase


class DummyModel(models.Model):
    pass


class TestBaseExportView(ViewTestCase):
    view_class = BaseExportView

    @patch("dbentry.site.views.export.super")
    def test_get_context_data_adds_queryset(self, super_mock):
        """Assert that get_context_data adds the queryset to the template context."""
        super_mock.return_value.get_context_data.return_value = {}
        queryset_mock = Mock()
        view = self.get_view(self.post_request(), queryset=queryset_mock, model=DummyModel)
        context_data = view.get_context_data()
        self.assertIn("queryset", context_data)
        self.assertEqual(context_data["queryset"], queryset_mock)


class TestExportActionView(ViewTestCase):
    view_class = ExportActionView

    def test_post_calls_get_if_action_not_confirmed(self):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel, queryset=Mock())
        with patch.object(view, "action_confirmed", new=Mock(return_value=False)):
            with patch.object(view, "get") as get_mock:
                view.post(request)
                get_mock.assert_called()

    @patch("dbentry.site.views.export.super")
    def test_post_calls_post_if_action_confirmed(self, super_mock):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel, queryset=Mock())
        post_mock = Mock()
        super_mock.return_value.post = post_mock
        with patch.object(view, "action_confirmed", new=Mock(return_value=True)):
            view.post(request)
            post_mock.assert_called()
