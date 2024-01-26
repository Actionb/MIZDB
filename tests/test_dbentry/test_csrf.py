from django import forms
from django.urls import reverse

from dbentry.csrf import csrf_failure, _restore_formset, CSRF_FORM_DATA_KEY
from tests.case import RequestTestCase, TestCase
from tests.model_factory import make
from tests.test_dbentry.models import Band, Genre


class TestRestoreFormset(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.rock, cls.spam = genres = [make(Genre, genre="Rock"), make(Genre, genre="Spam")]
        cls.pop = make(Genre, genre="Pop")
        cls.obj = make(Band, band_name="Testband", genre=genres)
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.formset_class = forms.inlineformset_factory(Band, Band.genre.through, fields=forms.ALL_FIELDS)
        self.formset = self.formset_class(instance=self.obj)

    def test_restore_formset_unbound_formset(self):
        """
        Assert that, for unbound formsets, _restore_formset adds all the data
        to `initial_extra`.
        """
        data = {"Band_genre-0-genre": [self.rock.pk], "Band_genre-1-genre": [self.spam.pk]}
        formset = _restore_formset(self.formset_class(instance=None), data)
        self.assertEqual(formset.initial_extra, [{"genre": self.rock.pk}, {"genre": self.spam.pk}, {}])
        self.assertEqual(formset.extra, 3)

    def test_restore_formset_bound_form_no_changes(self):
        """
        Assert that _restore_format does not add data to `initial_extra` if the
        data does not constitute a new addition.
        """
        data = {"Band_genre-0-genre": [self.rock.pk], "Band_genre-1-genre": [self.spam.pk]}
        formset = _restore_formset(self.formset_class(instance=self.obj), data)
        self.assertEqual(formset.initial_extra, [{}])
        self.assertEqual(formset.extra, 1)

    def test_restore_formset_bound_form_change(self):
        """
        Assert that _restore_formset sets the correct initial data on bound
        forms that would be changed by the request data.
        """
        data = {"Band_genre-0-genre": [self.rock.pk], "Band_genre-1-genre": [self.pop.pk]}
        formset = _restore_formset(self.formset_class(instance=self.obj), data)
        self.assertEqual(formset.forms[1].initial["genre"], self.pop.pk)

    def test_restore_formset_bound_form_addition(self):
        """
        Assert that _restore_formset adds new form data to `initial_extra`.
        """
        data = {
            "Band_genre-0-genre": [self.rock.pk],
            "Band_genre-1-genre": [self.spam.pk],
            "Band_genre-2-genre": [self.pop.pk],
        }
        formset = _restore_formset(self.formset_class(instance=self.obj), data)
        self.assertEqual(formset.initial_extra, [{"genre": self.pop.pk}, {}])
        self.assertEqual(formset.extra, 2)

    def test_restore_formset_ignores_empty_values(self):
        """
        Assert that _restore_formset does not add fields with empty values to
        `initial_extra`.
        """
        data = {"Band_genre-0-genre": [""], "Band_genre-1-genre": [self.spam.pk]}
        formset = _restore_formset(self.formset_class(instance=None), data)
        self.assertEqual(formset.initial_extra, [{"genre": self.spam.pk}, {}])
        self.assertEqual(formset.extra, 2)

    def test_restore_formset_ignores_fields_that_do_not_match_regex(self):
        """
        Assert that _restore_formset does not add fields that do not match the
        regex to `initial_extra`.
        """
        data = {"foo-bar": ["foobar"], "Band_genre-1-genre": [self.spam.pk]}
        formset = _restore_formset(self.formset_class(instance=None), data)
        self.assertEqual(formset.initial_extra, [{"genre": self.spam.pk}, {}])
        self.assertEqual(formset.extra, 2)


class TestCSRF(RequestTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Band)
        super().setUpTestData()

    def test_csrf_failure(self):
        """
        Assert that a POST request with an invalid CSRF token returns a 403
        response.
        """
        for view_name in ("admin:dbentry_band_delete", "dbentry_band_delete"):
            with self.subTest(view=view_name):
                url = reverse(view_name, args=[self.obj.pk])
                request = self.post_request(
                    url,
                    data={"csrfmiddlewaretoken": ""},
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
                self.assertURLEqual(response.url, reverse(login_view))

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
                self.assertURLEqual(response.url, reverse(login_view))

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
                self.assertURLEqual(response.url, reverse(index_view))
                self.assertMessageSent(request, "Abmeldung fehlgeschlagen")

    def test_csrf_failure_miz_site_add_or_change_page(self):
        """
        Assert that a CSRF failure on an add or change page of the MIZ site
        reloads the page with the form data preserved in the session.
        """
        urls = [
            reverse("dbentry_band_add"),
            reverse("dbentry_band_change", args=[self.obj.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                request = self.client.post(
                    url,
                    data={"band_name": "foo", "csrfmiddlewaretoken": "", "_continue": "1"},
                    user=self.super_user,
                ).wsgi_request
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 302)
                self.assertURLEqual(response.url, url)
                self.assertIn(CSRF_FORM_DATA_KEY, request.session)
                self.assertEqual(request.session[CSRF_FORM_DATA_KEY], {"band_name": ["foo"], "_continue": ["1"]})
                self.assertMessageSent(request, "Speichern fehlgeschlagen")

    def test_csrf_failure_admin_add_or_change_page(self):
        """
        Assert that a CSRF failure on an add or change page of the admin site
        creates a 403 response.
        """
        urls = [
            reverse("admin:dbentry_band_add"),
            reverse("admin:dbentry_band_change", args=[self.obj.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                request = self.client.post(
                    url,
                    data={"band_name": "foo", "csrfmiddlewaretoken": "", "_continue": "1"},
                    user=self.super_user,
                ).wsgi_request
                response = csrf_failure(request, "Token invalid.")
                self.assertEqual(response.status_code, 403)
