from unittest.mock import patch

from django.http import HttpResponseRedirect
from django.template import TemplateDoesNotExist
from django.test import TestCase
from django.test import override_settings
from django.urls import path, reverse

from dbentry.site.views.help import has_help_page, HelpView
from tests.case import ViewTestCase


def dummy_view(*args, **kwargs):
    pass


urlpatterns = [
    path("hilfe/index/", dummy_view, name="help_index"),
    path("hilfe/<path:page_name>/", dummy_view, name="help"),
]


class TestHasHelpPage(TestCase):

    def test_has_help_page(self):
        for has_page in (True, False):
            with self.subTest(has_help_page=has_page):
                with patch("dbentry.site.views.help.get_template") as get_template_mock:
                    if not has_page:
                        get_template_mock.side_effect = TemplateDoesNotExist(msg="")
                    self.assertEqual(has_help_page("foo"), has_page)


@override_settings(ROOT_URLCONF="tests.test_site.urls")
class TestHelpView(ViewTestCase):
    view_class = HelpView

    @patch("dbentry.site.views.help.has_help_page")
    def test_get(self, has_help_page_mock):
        """Assert that 'get' calls super().get() if a help page exists."""
        has_help_page_mock.return_value = True
        request = self.get_request()
        view = self.get_view(kwargs={"page_name": "foo"})
        with patch("dbentry.site.views.help.super") as super_mock:
            view.get(request)
            super_mock.assert_called()

    @patch("dbentry.site.views.help.has_help_page")
    def test_get_no_help_page(self, has_help_page_mock):
        """
        Assert that 'get' sends a user message if the request help page does
        not exist.
        """
        has_help_page_mock.return_value = False
        response = self.get_response(reverse("help", kwargs={"page_name": "foo"}))
        self.assertMessageSent(response.wsgi_request, "Hilfe Seite für 'foo' nicht gefunden.")
        self.assertRedirects(response, reverse("help_index"))

    @patch("dbentry.site.views.help.has_help_page")
    def test_get_no_page_name(self, has_help_page_mock):
        """
        Assert that 'get' responds with the help index if no ``page_name``
        is given.
        """
        has_help_page_mock.return_value = True
        request = self.get_request()
        view = self.get_view(kwargs={})
        response = view.get(request)
        self.assertIsInstance(response, HttpResponseRedirect)
        self.assertURLEqual(response.url, reverse("help_index"))

    def test_get_template_names_unquotes(self):
        """Assert that get_template_names 'URL unquotes' the page names."""
        view = self.get_view(kwargs={"page_name": "ä"})
        self.assertEqual(view.get_template_names(), ["help/ä.html"])

    def test_title(self):
        view = self.get_view(kwargs={"page_name": "föö_bär"})
        self.assertEqual(view.title, "Föö Bär - Hilfe")
