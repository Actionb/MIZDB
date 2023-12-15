"""Tests for the `searchbar search` view."""
import json
from unittest.mock import patch, Mock

from django.test import override_settings
from django.urls import path, reverse

from dbentry.site.views.search import SearchbarSearch, SiteSearchView
from tests.case import ViewTestCase
from tests.model_factory import make
from tests.test_site.models import Band, Musician


def dummy_view(request, *args, **kwargs):  # noqa
    return None


class URLConf:
    urlpatterns = [
        path("band/<path:object_id>/change/", dummy_view, name="test_site_band_change"),
        path("band/", dummy_view, name="test_site_band_changelist"),
        path("musician/<path:object_id>/change/", dummy_view, name="test_site_musician_change"),
        path("musician/", dummy_view, name="test_site_musician_changelist"),
        path("search/", SearchbarSearch.as_view(), name="search"),
        path("site_search/", SiteSearchView.as_view(), name="site_search"),
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestSearchbarSearch(ViewTestCase):
    model = Band
    view_class = SearchbarSearch

    @classmethod
    def setUpTestData(cls):
        cls.foo = make(Band, name="The Foo Fighters")
        cls.bar = make(Band, name="Foo and Bar")
        cls.paul = make(Musician, name="Paul Foo")
        cls.keith = make(Musician, name="Keith Bar")
        super().setUpTestData()

    @patch("dbentry.site.views.search.miz_site")
    def test(self, site_mock):
        site_mock.model_list = [("", [Band._meta, Musician._meta])]
        q = "foo"
        response = self.get_response(reverse("search"), data={"q": q})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("total_count", data)
        self.assertEqual(data["total_count"], 3)
        self.assertIn("results", data)
        results = data["results"]
        self.assertEqual(len(results), 2)  # two models Band and Musician
        bands, musicians = results
        self.assertEqual(bands["model_name"], "band")
        self.assertHTMLEqual(
            bands["changelist_link"], f'<a href="/band/?q={q}" class="text-decoration-none">BANDS (2)</a>'
        )
        details = bands["details"]
        self.assertEqual(len(details), 2)
        self.assertHTMLEqual(details[0], f'<a href="/band/{self.foo.pk}/change/">The Foo Fighters</a>')
        self.assertHTMLEqual(details[1], f'<a href="/band/{self.bar.pk}/change/">Foo and Bar</a>')

        self.assertEqual(musicians["model_name"], "musician")
        self.assertHTMLEqual(
            musicians["changelist_link"], f'<a href="/musician/?q={q}" class="text-decoration-none">MUSICIAN</a>'
        )
        details = musicians["details"]
        self.assertEqual(len(details), 1)
        self.assertHTMLEqual(details[0], f'<a href="/musician/{self.paul.pk}/change/">Paul Foo</a>')

    @patch("dbentry.site.views.search.JsonResponse")
    def test_get_many_results_no_details(self, json_response_mock):
        """
        Assert that the results do not contain result details if there are many
        results.
        """
        queryset_mock = Mock()
        queryset_mock.count.return_value = 20
        request = self.get_request(data={"q": "foo"})
        view = self.get_view(request)
        with patch.object(view, "get_results") as get_results_mock:
            get_results_mock.return_value = [queryset_mock]
            view.get(request)
            json_response_mock.assert_called()
            (data, *_), _kwargs = json_response_mock.call_args
            results = data["results"]
            band_results = results[0]
            self.assertNotIn("details", band_results.keys())


class TestUnit(ViewTestCase):
    view_class = SearchbarSearch

    @patch("dbentry.site.views.search.SearchbarSearch._get_model_results")
    def test_get_results_excludes_empty_querysets(self, get_results_mock):
        """Assert that empty querysets are excluded from the result list."""
        view = self.get_view()
        for exists in (True, False):
            with self.subTest(exists=exists):
                get_results_mock.return_value.exists.return_value = exists
                results = view._get_results("q", [Mock()])
                if exists:
                    self.assertTrue(results)
                else:
                    self.assertFalse(results)

    def test_get_model_results_ranked_false(self):
        """Assert that _get_model_results calls search with ranked=False."""
        queryset_mock = Mock()
        view = self.get_view()
        view._get_model_results("q", queryset_mock)
        queryset_mock.search.assert_called_with("q", ranked=False)

    def test_get_changelist_link_label_single_result(self):
        """
        Assert that the verbose_name is returned if the queryset contains
        exactly one result.
        """
        options_mock = Mock(verbose_name="Verbose Mock")
        queryset_mock = Mock(**{"count.return_value": 1})
        view = self.get_view()
        # Note that _get_changelist_link_label calls upper on the final label.
        self.assertEqual(view._get_changelist_link_label(queryset_mock, options_mock), "VERBOSE MOCK")

    def test_get_changelist_link_label_multiple_results(self):
        """
        Assert that a string containing the verbose_name_plural and the queryset
        count is returned if the queryset contains more than one result.
        """
        options_mock = Mock(verbose_name_plural="Verbose Plural Mock")
        queryset_mock = Mock(**{"count.return_value": 42})
        view = self.get_view()
        # Note that _get_changelist_link_label calls upper on the final label.
        self.assertEqual(view._get_changelist_link_label(queryset_mock, options_mock), "VERBOSE PLURAL MOCK (42)")

    def test_get_changelist_link_no_url(self):
        """Assert that just the label is returned if no url is given."""
        view = self.get_view()
        self.assertEqual(view._get_changelist_link("", "label", True), "label")

    @patch("dbentry.site.views.search.create_hyperlink")
    def test_get_changelist_link_popup(self, create_link_mock):
        """
        Assert that the link factory function is called with target=_blank if
        popup is True.
        """
        view = self.get_view()
        view._get_changelist_link("url", "label", popup=True)
        create_link_mock.assert_called()
        args, kwargs = create_link_mock.call_args
        self.assertIn("target", kwargs)
        self.assertEqual(kwargs["target"], "_blank")

    @patch("dbentry.site.views.search.create_hyperlink")
    def test_get_changelist_link_no_popup(self, create_link_mock):
        """
        Assert that the link factory function is called without target=_blank if
        popup is False.
        """
        view = self.get_view()
        view._get_changelist_link("url", "label", popup=False)
        create_link_mock.assert_called()
        args, kwargs = create_link_mock.call_args
        self.assertNotIn("target", kwargs)

    @patch("dbentry.site.views.search.get_changelist_url")
    def test_get_changelist_link_url_search_term_query_string(self, get_changelist_mock):
        """
        Assert that a query string containing the search term is appended to
        the URL.
        """
        get_changelist_mock.return_value = "foo/"
        view = self.get_view()
        url = view._get_changelist_link_url(request="request", model="model", q="bar")
        self.assertIn("q=bar", url)

    @patch("dbentry.site.views.search.get_changelist_url")
    def test_get_changelist_link_no_url_search_term_query_string(self, get_changelist_mock):
        """
        Assert that a query string containing the search term is not appended to
        the URL when get_changelist_url does not return a URL.
        """
        get_changelist_mock.return_value = ""
        view = self.get_view()
        url = view._get_changelist_link_url(request="request", model="model", q="bar")
        self.assertNotIn("q=bar", url)


@override_settings(ROOT_URLCONF=URLConf)
class TestSiteSearchView(ViewTestCase):
    view_class = SiteSearchView

    @classmethod
    def setUpTestData(cls):
        cls.foo = make(Band, name="The Foo Fighters")
        cls.bar = make(Band, name="Foo and Bar")
        cls.paul = make(Musician, name="Paul Foo")
        cls.keith = make(Musician, name="Keith Bar")
        super().setUpTestData()

    def test_get_context_data_results(self):
        """Assert that the results are included in the template context."""
        view = self.get_view(self.get_request(reverse("site_search"), data={"q": "foo"}))
        with patch.object(view, "get_models") as get_models_mock:
            get_models_mock.return_value = [Band, Musician]
            with patch("dbentry.site.views.search.super") as super_mock:
                super_mock.return_value.get_context_data.return_value = {}
                context_data = view.get_context_data()
        self.assertIn("results", context_data)
        self.assertEqual(
            context_data["results"],
            [
                '<a href="/band/?q=foo" class="text-decoration-none">Bands (2)</a>',
                '<a href="/musician/?q=foo" class="text-decoration-none">Musician</a>',
            ],
        )
