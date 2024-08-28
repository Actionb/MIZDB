"""Tests for the dbentry.site templates."""

from bs4 import BeautifulSoup
from django.contrib.auth.models import AnonymousUser
from django.template import loader
from django.test import override_settings
from django.urls import reverse

from tests.case import UserTestCase


class RenderTestCase(UserTestCase):
    template_name = None

    def get_context(self):
        return {}

    def render(self, template, context=None, using=None):
        return loader.render_to_string(template, context or self.get_context(), using=using)

    def get_soup(self, template, context=None, using=None):
        return BeautifulSoup(self.render(template, context, using), "html.parser")


@override_settings(ROOT_URLCONF="tests.test_site.urls")
class TestBase(RenderTestCase):
    template_name = "mizdb/base.html"

    def test_user_account_anonymous(self):
        """Check the contents of the user account block for anonymous users."""
        soup = self.get_soup(self.template_name, {"user": AnonymousUser()})
        account = str(soup.select("#user-account")[0])
        login_url = reverse("login")
        self.assertInHTML(f'<li><a class="dropdown-item" href="{login_url}">Anmelden</a></li>', account)

    def test_user_account_authenticated(self):
        """
        Check the contents of the user account block for authenticated users.

        The block should be a dropdown containing a welcome message, a link to
        the password change page and a logout form.
        """
        user = self.staff_user
        user.first_name = "Alice"
        csrf_token = "foo"

        soup = self.get_soup(self.template_name, {"user": user, "csrf_token": csrf_token})
        account = str(soup.select("#user-account")[0])

        welcome_message = (
            '<li><span class="dropdown-item-text">Willkommen, <strong>Alice</strong></span></li>'
            '<li><hr class="dropdown-divider"></li>'
        )
        pw_change = f'<li><a class="dropdown-item" href="{reverse("password_change")}">Passwort ändern</a></li>'
        logout_form = (
            f'<li><form id="logout-form" method="post" action="{reverse("logout")}">'
            f'<input name="csrfmiddlewaretoken" type="hidden" value="{csrf_token}">'
            '<button class="dropdown-item" type="submit">Abmelden</button>'
            '</form></li>'
        )

        expected_content = [
            ("welcome message", welcome_message),
            ("password change link", pw_change),
            ("logout form", logout_form),
        ]
        for content_type, html in expected_content:
            with self.subTest(content_type=content_type):
                self.assertInHTML(html, account, msg_prefix=account)
