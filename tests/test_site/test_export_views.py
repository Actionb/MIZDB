from unittest.mock import patch, Mock

from django.db import models

from dbentry.site.views.export import BaseExportView, ExportActionView
from tests.case import ViewTestCase


class DummyModel(models.Model):
    pass


class TestBaseExportView(ViewTestCase):
    view_class = BaseExportView

    @patch("dbentry.site.views.export.super")
    def test_get_context_data_adds_queryset(self, super_mock):
        """
        Assert that get_context_data adds the queryset to the template context.
        """
        super_mock.return_value.get_context_data.return_value = {}
        queryset_mock = Mock()
        view = self.get_view(self.post_request(), queryset=queryset_mock, model=DummyModel)
        context_data = view.get_context_data()
        self.assertIn("queryset", context_data)
        self.assertEqual(context_data["queryset"], queryset_mock)

    def test_action_confirmed_true(self):
        request = self.post_request(data={"post": ""})
        view = self.get_view(request, model=DummyModel)
        self.assertTrue(view.action_confirmed(request))

    def test_action_confirmed_false(self):
        request = self.post_request(data={})
        view = self.get_view(request, model=DummyModel)
        self.assertFalse(view.action_confirmed(request))

    @patch("dbentry.site.views.export.super")
    def test_get_form_kwargs(self, super_mock):
        """
        Assert that the kwargs returned by get_form_kwargs only includes 'data'
        if the action was confirmed.
        """
        super_mock.return_value.get_form_kwargs.return_value = {"data": ""}
        view = self.get_view(request=self.post_request(), model=DummyModel)
        with patch.object(view, "action_confirmed") as action_confirmed_mock:
            for action_confirmed in (True, False):
                action_confirmed_mock.return_value = action_confirmed
                with self.subTest(action_confirmed=action_confirmed):
                    form_kwargs = view.get_form_kwargs()
                    if action_confirmed:
                        self.assertIn("data", form_kwargs)
                    else:
                        self.assertNotIn("data", form_kwargs)


class TestExportActionView(ViewTestCase):
    view_class = ExportActionView

    @patch("dbentry.site.views.export.super")
    def test_get_context_data_adds_is_changelist_action(self, super_mock):
        super_mock.return_value.get_context_data.return_value = {}
        view = self.get_view(self.post_request(), model=DummyModel)
        context_data = view.get_context_data()
        self.assertIn("is_changelist_action", context_data)
        self.assertTrue(context_data["is_changelist_action"])

    @patch("dbentry.site.views.export.super")
    def test_get_context_data_adds_action_selection_name(self, super_mock):
        super_mock.return_value.get_context_data.return_value = {}
        view = self.get_view(self.post_request(), model=DummyModel)
        with patch("dbentry.site.views.export.ACTION_SELECTED_ITEM", new="foo"):
            context_data = view.get_context_data()
            self.assertIn("action_selection_name", context_data)
            self.assertEqual(context_data["action_selection_name"], "foo")

    @patch("dbentry.site.views.export.super")
    def test_post_calls_get_if_action_not_confirmed(self, super_mock):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel)
        get_mock = Mock()
        super_mock.return_value.get = get_mock
        with patch.object(view, "action_confirmed", new=Mock(return_value=False)):
            view.post(request)
            get_mock.assert_called()

    @patch("dbentry.site.views.export.super")
    def test_post_calls_post_if_action_confirmed(self, super_mock):
        request = self.post_request()
        view = self.get_view(request, model=DummyModel)
        post_mock = Mock()
        super_mock.return_value.post = post_mock
        with patch.object(view, "action_confirmed", new=Mock(return_value=True)):
            view.post(request)
            post_mock.assert_called()
