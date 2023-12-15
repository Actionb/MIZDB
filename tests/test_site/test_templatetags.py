from unittest.mock import Mock
from urllib.parse import parse_qsl, urlparse, urlencode

# noinspection PyPackageRequirements
from bs4 import BeautifulSoup
from django.test.utils import override_settings
from django.urls import path, reverse
from mizdb_tomselect.views import IS_POPUP_VAR

from dbentry.site.templatetags.mizdb import (
    add_preserved_filters,
    reset_ordering_link,
    formset_has_errors,
    get_actionlist_item,
    remove_popup_param,
)
from dbentry.site.views.base import BaseListView, ORDER_VAR
from tests.case import ViewTestCase
from tests.test_site.models import Band


class Changelist(BaseListView):
    model = Band


class URLConf:
    urlpatterns = [
        path("band/", Changelist.as_view(), name="test_site_band_changelist"),
        path("band/add", lambda r: None, name="test_site_band_add"),
        path("band/<path:object_id>/", lambda r: None, name="test_site_band_change"),
    ]


def get_query_params(url):
    """Return a dictionary of the query string parameters in the given URL."""
    return dict(parse_qsl(list(urlparse(url))[4]))


def get_soup(html):
    """Parse the html using BeautifulSoup."""
    return BeautifulSoup(html, features="html.parser")


def get_link_url(html):
    """Parse the html and return the href of the first anchor element."""
    return get_soup(html).a.get("href")


def get_mock_entry(is_addition=False, is_change=False, is_deletion=False):
    """Return a mocked django admin LogEntry instance."""
    entry = Mock()
    entry.object_repr = "Foo"
    entry.object_id = "1"
    entry.content_type.model_class.return_value = Band
    entry.is_addition.return_value = is_addition
    entry.is_change.return_value = is_change
    entry.is_deletion.return_value = is_deletion
    return entry


@override_settings(ROOT_URLCONF=URLConf)
class TestTags(ViewTestCase):
    view_class = Changelist

    def changelist_filters(self):
        """Return a query string of changelist filters for add_preserved_filters."""
        return urlencode({"_changelist_filters": urlencode({"q": "Foo"})})

    def preserved_filters_context(self):
        """Return the context argument for add_preserved_filters."""
        return {"opts": Band._meta, "preserved_filters": self.changelist_filters()}

    def test_add_preserved_filters(self):
        """
        Assert that the changelist filters are included in the query string
        under a special query parameter.
        """
        url = reverse("test_site_band_change", args=[1])
        preserved_filters = add_preserved_filters(base_url=url, context=self.preserved_filters_context())
        query_params = get_query_params(preserved_filters)
        self.assertIn("_changelist_filters", query_params)
        self.assertIn("q=Foo", query_params["_changelist_filters"])

    def test_add_preserved_filters_to_changelist(self):
        """
        Assert that the changelist filters are added to the query string
        directly if the URL points back to a changelist.
        """
        url = reverse("test_site_band_changelist")
        preserved_filters = add_preserved_filters(base_url=url, context=self.preserved_filters_context())
        query_params = get_query_params(preserved_filters)
        self.assertIn("q", query_params)
        self.assertEqual("Foo", query_params["q"])

    def test_reset_ordering_link(self):
        """
        Assert that reset_ordering_link returns a link without the ordering
        query parameter.
        """
        changelist = self.get_view(self.get_request(data={ORDER_VAR: "1"}))
        link = reset_ordering_link(changelist)
        query_params = get_query_params(get_link_url(link))
        self.assertNotIn(ORDER_VAR, query_params)

    def test_reset_ordering_link_no_order_var(self):
        """
        Assert that reset_ordering_link returns an empty string if the ordering
        query parameter was not present in the request.
        """
        changelist = self.get_view(self.get_request())
        link = reset_ordering_link(changelist)
        self.assertEqual(link, "")

    def test_formset_has_errors(self):
        """Assert that formset_has_errors validates bound formsets."""
        is_valid_mock = Mock()
        formset = Mock(is_bound=True, is_valid=is_valid_mock)
        formset_has_errors(formset)
        is_valid_mock.assert_called()

    def test_formset_has_errors_unbound(self):
        """Assert that formset_has_errors does not validate unbound formsets."""
        is_valid_mock = Mock()
        formset = Mock(is_bound=False, is_valid=is_valid_mock)
        self.assertFalse(formset_has_errors(formset))
        is_valid_mock.assert_not_called()

    def test_get_actionlist_item(self):
        """Assert that an action list item contains the expected title and URL."""
        for is_add in (True, False):
            with self.subTest(is_add=is_add):
                entry = get_mock_entry(is_addition=is_add, is_change=not is_add)
                actionlist_item = get_actionlist_item(entry)
                title = "Hinzugefügt" if is_add else "Geändert"
                self.assertEqual(actionlist_item["title"], title)
                change_url = get_link_url(actionlist_item["change_link"])
                self.assertEqual(change_url, reverse("test_site_band_change", args=[1]))

    def test_get_actionlist_item_delete(self):
        """Assert that action list items for deletions do not contain a change URL."""
        entry = get_mock_entry(is_deletion=True)
        actionlist_item = get_actionlist_item(entry)
        self.assertEqual(actionlist_item["title"], "Gelöscht")
        self.assertEqual(actionlist_item["change_link"], entry.object_repr)

    def test_remove_popup_param(self):
        for request_data in ({IS_POPUP_VAR: "1"}, {}):
            with self.subTest(is_popup=IS_POPUP_VAR in request_data):
                request = self.get_request("/", data={"foo": "bar", **request_data})
                self.assertEqual(remove_popup_param(request), "?foo=bar")
