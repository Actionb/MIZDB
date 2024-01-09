from urllib.parse import urlparse

from django.urls import reverse, resolve

from dbentry.csrf import csrf_failure
from tests.case import RequestTestCase


class TestCSRF(RequestTestCase):
    def test_csrf_failure(self):
        """
        Assert that a POST request with an invalid CSRF token returns a 403
        response.
        """
        for view_name in ("admin:dbentry_band_add", "dbentry_band_add"):
            with self.subTest(view=view_name):
                request = self.post_request(
                    reverse(view_name),
                    data={"band_name": "foo", "csrfmiddlewaretoken": "", "_continue": "1"},
                    user=self.super_user,
                )
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 403)

    def test_csrf_failure_login_by_logged_in_user(self):
        """
        Assert that an authenticated user is redirected to the login page upon
        sending a login request with an invalid CSRF token.

        (this can happen when the user has two tabs open and tries to log in
        with both tabs, one after another)
        """
        for login_view in ("admin:login", "login"):
            with self.subTest(url_name=login_view):
                request = self.rf.post(reverse(login_view))
                request.user = self.super_user
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(resolve(urlparse(response.url).path).route, reverse(login_view)[1:])

    def test_csrf_failure_logout_by_logged_out_user(self):
        """
        Assert that a csrf failure from sending a logout request without a user
        does not create a CSRF failure response and redirects to the login page.

        (this can happen when the user has two tabs open and attempts to log
        out in both tabs, one after another)
        """
        for logout_view, login_view in [("admin:logout", "admin:login"), ("logout", "login")]:
            with self.subTest(url_name=logout_view):
                request = self.rf.post(reverse(logout_view))
                request.user = None
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse(login_view))

    def test_csrf_failure_logout_by_logged_in_user(self):
        """
        Assert that a user message is issued when the CSRF token is invalid on
        a logout request by an authenticated user.
        """
        for logout_view, index_view in [("admin:logout", "admin:index"), ("logout", "index")]:
            with self.subTest(url_name=logout_view):
                # We need a request that was processed by the required
                # middlewares - for that we need to use the test client. Using
                # the client will however actually log out the user, which
                # means we need to add the user back to the request.
                request = self.client.post(reverse(logout_view), user=self.super_user).wsgi_request
                request.user = self.super_user
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse(index_view))
                self.assertMessageSent(request, "Abmeldung fehlgeschlagen")
