from unittest.mock import Mock, patch

from django.urls import reverse
from mizdb_tomselect.views import SEARCH_VAR

from dbentry import models as _models
from dbentry.autocomplete.views import (
    AutocompleteAusgabe,
    AutocompleteAutor,
    AutocompleteBuchband,
    AutocompleteMagazin,
    AutocompleteMostUsed,
    AutocompletePerson,
    MIZAutocompleteView,
)
from tests.case import DataTestCase, ViewTestCase
from tests.model_factory import make
from tests.test_autocomplete.models import Ausgabe


class TestMIZAutocompleteView(ViewTestCase):
    view_class = MIZAutocompleteView

    def test_get_page_results(self):
        """Assert that overview is called on the page object list."""
        overview_mock = Mock()
        page_mock = Mock(object_list=Mock(overview=overview_mock))
        view = self.view_class()
        view.values_select = ["foo", "bar"]
        view.get_page_results(page_mock)
        overview_mock.assert_called_with("foo", "bar")

    def test_search(self):
        """Assert that search() is only called when a search term is given."""
        view = self.view_class()
        for q in ("foo", ""):
            search_mock = Mock()
            with self.subTest(search_term=q):
                view.search(Mock(search=search_mock), q)
                if q:
                    search_mock.assert_called()
                else:
                    search_mock.assert_not_called()

    def test_order_queryset(self):
        """
        Assert that super.order_queryset is only called when no search term is
        given.
        """
        view = self.view_class()
        for q in ("foo", ""):
            view.q = q
            with self.subTest(search_term=q):
                with patch("dbentry.autocomplete.views.AutocompleteView.order_queryset") as super_mock:
                    view.order_queryset(None)
                    if q:
                        super_mock.assert_not_called()
                    else:
                        super_mock.assert_called()

    def test_create_object_adds_logentry(self):
        """Assert that create_object calls log_addition for the created object."""
        request = self.post_request(
            "/", data={"model": f"{Ausgabe._meta.app_label}.{Ausgabe._meta.model_name}", "create_field": "name"}
        )
        view = self.get_view(request)
        with patch("dbentry.autocomplete.views.AutocompleteView.create_object"):
            with patch("dbentry.autocomplete.views.log_addition") as log_mock:
                view.create_object(None)
                log_mock.assert_called()


class TestAutocompleteAusgabe(ViewTestCase):
    view_class = AutocompleteAusgabe

    def test_order_queryset(self):
        """
        Assert that chronological_order is only called when no search term is
        given.
        """
        view = self.view_class()
        for q in ("foo", ""):
            view.q = q
            chronological_order_mock = Mock()
            with self.subTest(search_term=q):
                view.order_queryset(Mock(chronological_order=chronological_order_mock))
                if q:
                    chronological_order_mock.assert_not_called()
                else:
                    chronological_order_mock.assert_called()


class TestAutocompleteAutor(ViewTestCase):
    model = _models.Autor
    view_class = AutocompleteAutor

    def test_create_object(self):
        """Assert that create_object creates the expected Autor object."""
        request = self.get_request(
            data={"create-field": "cf", "model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"}
        )
        view = self.get_view(request)
        created = view.create_object({"cf": "Bob Tester (BT)"})
        self.assertTrue(created.pk)
        self.assertTrue(self.model.objects.get(pk=created.pk))
        self.assertTrue(
            self.model.objects.filter(person__vorname="Bob", person__nachname="Tester", kuerzel="BT").exists()
        )

    @patch("dbentry.autocomplete.views.log_addition")
    def test_create_object_adds_log_entry(self, log_addition_mock):
        """Assert that log entries are added for the created objects."""
        request = self.get_request(
            data={"create-field": "cf", "model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"}
        )
        view = self.get_view(request)
        obj = view.create_object({"cf": "Alice Testman (AT)"})
        self.assertEqual(len(log_addition_mock.call_args_list), 2)
        person_call, autor_call = log_addition_mock.call_args_list
        self.assertEqual(person_call.args, (request.user.pk, obj.person))
        self.assertEqual(autor_call.args, (request.user.pk, obj))

    def test_create_object_only_kuerzel(self):
        """Assert that no Person instance is created if only the kuerzel is given."""
        request = self.get_request(
            data={"create-field": "cf", "model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"}
        )
        view = self.get_view(request)
        created = view.create_object({"cf": "(BT)"})
        self.assertTrue(created.pk)
        self.assertFalse(_models.Person.objects.exists())


class TestAutocompleteBuchband(ViewTestCase):
    model = _models.Buch
    view_class = AutocompleteBuchband

    @classmethod
    def setUpTestData(cls):
        cls.buchband = make(cls.model, is_buchband=True)
        cls.not_buchband = make(cls.model, is_buchband=False)
        super().setUpTestData()

    def test_queryset_only_contains_buchband(self):
        """
        Assert that get_queryset does not return Buch instances that are not
        flagged as 'buchband'.
        """
        request = self.get_request(data={"model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"})
        view = self.get_view(request)
        queryset = view.get_queryset()
        self.assertNotIn(self.not_buchband, queryset)
        self.assertIn(self.buchband, queryset)


class TestAutocompleteMagazin(DataTestCase, ViewTestCase):
    model = _models.Magazin
    view_class = AutocompleteMagazin

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(cls.model, issn="12345679")
        super().setUpTestData()

    def test_search(self):
        """Assert that a search term that is a valid ISSN gets compacted."""
        view = self.view_class()
        for q, expected, is_valid_issn in [("1234-5679", "12345679", True), ("1234-5670", "1234-5670", False)]:
            with self.subTest(search_term=q, is_valid_issn=is_valid_issn):
                with patch("dbentry.autocomplete.views.MIZAutocompleteView.search") as super_mock:
                    view.search(None, q)
                    super_mock.assert_called_with(None, expected)

    def test_search_by_issn(self):
        """Assert that an ISSN can be used to search."""
        for issn in ("1234-5679", "12345679"):
            with self.subTest(issn=issn):
                request = self.get_request(
                    "/", data={"model": f"{self.model._meta.app_label}.{self.model._meta.model_name}", SEARCH_VAR: issn}
                )
                view = self.get_view(request)
                self.assertIn(self.obj, view.get_queryset())


class TestAutocompletePerson(ViewTestCase):
    model = _models.Person
    view_class = AutocompletePerson

    def test_create_object(self):
        """Assert that create_object creates the expected Autor object."""
        request = self.get_request(
            data={"create-field": "cf", "model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"}
        )
        view = self.get_view(request)
        created = view.create_object({"cf": "Bob Tester"})
        self.assertTrue(created.pk)
        self.assertTrue(self.model.objects.get(pk=created.pk))
        self.assertTrue(self.model.objects.filter(vorname="Bob", nachname="Tester").exists())

    @patch("dbentry.autocomplete.views.log_addition")
    def test_create_object_adds_log_entry(self, log_addition_mock):
        """Assert that log entries are added for the created objects."""
        request = self.get_request(
            data={"create-field": "cf", "model": f"{self.model._meta.app_label}.{self.model._meta.model_name}"}
        )
        view = self.get_view(request)
        view.create_object({"cf": "Alice Testman"})
        log_addition_mock.assert_called()


class TestAutocompleteMostUsed(ViewTestCase):
    view_class = AutocompleteMostUsed

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.most_used = most_used = make(_models.Schlagwort, schlagwort="Most Used")
        cls.second_most_used = second_most_used = make(_models.Schlagwort, schlagwort="Second Most Used")
        cls.not_used = make(_models.Schlagwort)
        cls.artikel1 = make(_models.Artikel, schlagwort=[most_used])
        cls.artikel2 = make(_models.Artikel, schlagwort=[most_used, second_most_used])

    def test(self):
        request_data = {"model": "dbentry.Schlagwort", self.view_class.page_kwarg: "1"}
        response = self.client.get(reverse("autocomplete_schlagwort"), data=request_data)
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0]["id"], self.most_used.pk)
        self.assertEqual(results[1]["id"], self.second_most_used.pk)
        self.assertEqual(results[2]["id"], self.not_used.pk)

    def test_search_term(self):
        request_data = {"model": "dbentry.Schlagwort", self.view_class.page_kwarg: "1", "q": "Second Most Used"}
        response = self.client.get(reverse("autocomplete_schlagwort"), data=request_data)
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertTrue(len(results), 1)
        self.assertEqual(results[0]["id"], self.second_most_used.pk)

    def test_order_queryset(self):
        """
        Assert that queryset.order_by_most_used is called when no search term
        is given.
        """
        order_by_most_used_mock = Mock()
        queryset_mock = Mock(order_by_most_used=order_by_most_used_mock)
        with patch("dbentry.autocomplete.views.super") as super_mock:
            super_mock.return_value.order_queryset.return_value = queryset_mock
            view = self.get_view(self.get_request(data={"model": "dbentry.Schlagwort"}))
            view.order_queryset(_models.Schlagwort.objects.all())
            order_by_most_used_mock.assert_called()

    def test_order_queryset_search_term(self):
        """
        Assert that queryset.order_by_most_used is not called when a search
        term is given.
        """
        order_by_most_used_mock = Mock()
        queryset_mock = Mock(order_by_most_used=order_by_most_used_mock)
        with patch("dbentry.autocomplete.views.super") as super_mock:
            super_mock.return_value.order_queryset.return_value = queryset_mock
            view = self.get_view(self.get_request(data={"model": "dbentry.Schlagwort"}))
            view.q = "Foo"
            view.order_queryset(_models.Schlagwort.objects.all())
            order_by_most_used_mock.assert_not_called()

    def test_no_field_artikel(self):
        """
        Assert that exceptions raised from the queryset model not having a
        relation to model `Artikel` are caught.
        """
        view = self.get_view(self.get_request(data={"model": "dbentry.Buch"}))
        view.order_queryset(_models.Buch.objects.all())
