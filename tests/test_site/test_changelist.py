from unittest import expectedFailure
from unittest.mock import call, patch, Mock
from urllib.parse import unquote

from django.test import override_settings
from django.urls import reverse, path
from django.views import View

from dbentry.site.views.base import BaseListView, SEARCH_VAR, ORDER_VAR
from tests.case import ViewTestCase, DataTestCase
from tests.model_factory import make
from tests.test_site.models import Band, Musician, Country


class ChangelistTestCase(DataTestCase, ViewTestCase):
    changelist_path = ""
    change_path = ""
    add_path = ""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        opts = cls.model._meta
        url_name = f"{opts.app_label}_{opts.model_name}"
        if not cls.changelist_path:
            cls.changelist_path = reverse(url_name + "_changelist")
        if not cls.change_path:
            cls.change_path = unquote(reverse(url_name + "_change", args=["{pk}"]))
        if not cls.add_path:
            cls.add_path = reverse(url_name + "_add")

    def get_annotated_model_obj(self, obj):
        """Apply the view's changelist annotations to the given object."""
        return self.queryset.overview().filter(pk=obj.pk).get()


class BandListView(BaseListView):
    model = Band

    list_display = ["name", "alias", "members", "origin", "unsortable"]

    # @formatter:off
    def members(self, obj):
        return obj.members_list
    members.description = "Members"
    members.ordering = "members_list"

    def unsortable(self, obj):
        return "This field cannot be sorted against."
    unsortable.description = "Ignore This"
    # @formatter:on

    def some_method(self, obj):
        pass


class URLConf:
    app_name = "test_site"
    urlpatterns = [
        path("add/", View.as_view(), name="test_site_band_add"),
        path("<path:object_id>/change/", View.as_view(), name="test_site_band_change"),
        path("", BandListView.as_view(), name="test_site_band_changelist"),
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestBaseListView(ChangelistTestCase):
    model = Band
    view_class = BandListView

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.origin = make(Country, name="United Kingdom")
        cls.obj = make(cls.model, name="Led Zeppelin", alias="Zepp", origin=cls.origin)
        cls.jimmy = make(Musician, name="Jimmy Page", band=cls.obj)
        cls.robert = make(Musician, name="Robert Plant", band=cls.obj)

    def test_lookup_field(self):
        """
        Assert that _lookup_field returns the expected model field or view
        method with the expected label.
        """
        view = self.get_view(self.get_request())
        test_data = [
            # name, (expected attr and label)
            ("alias", (self.model._meta.get_field("alias"), "Band Alias")),  # model field
            ("unsortable", (view.unsortable, "Ignore This")),  # method with a description
            ("some_method", (view.some_method, "Some method")),  # method without a description
            ("foo_bar", (None, "Foo bar")),  # can't resolve name
        ]
        for name, expected in test_data:
            with self.subTest(name=name):
                self.assertEqual(view._lookup_field(name), expected)

    def test_get_result_headers(self):
        """
        Assert that get_result_headers returns the expected list of table
        header labels.
        """
        headers = self.get_view(self.get_request()).get_result_headers()
        self.assertEqual(
            headers,
            [
                {"text": "Name"},
                {"text": "Band Alias"},
                {"text": "Members"},
                {"text": "Origin Country"},
                {"text": "Ignore This"},
            ],
        )

    def test_get_result_headers_no_list_display(self):
        """
        Assert that get_result_headers returns some default when the view does
        not declare list_display.
        """
        view = self.get_view(self.get_request(), list_display_links=None)
        with patch.object(view, "list_display", new=[]):
            with patch.object(self.model._meta, "verbose_name", new="Foo Bar"):
                self.assertEqual(view.get_result_headers(), [{"text": "Foo Bar"}])

    def test_add_list_display_annotations(self):
        """
        Assert that add_list_display_annotations calls the queryset's overview
        method if it exists.
        """
        view = self.get_view()
        overview_mock = Mock()
        for queryset, has_overview in [(Mock(), False), (Mock(overview=overview_mock), True)]:
            with self.subTest(has_overview=has_overview):
                view.add_list_display_annotations(queryset)
                if has_overview:
                    overview_mock.assert_called()
                else:
                    overview_mock.assert_not_called()
            overview_mock.reset_mock()

    def test_get_result_rows(self):
        """
        Assert that get_results_rows calls get_result_row on every item of the
        passed in object_list.
        """
        object_list = ["foo", "bar"]
        view = self.get_view()
        with patch.object(view, "get_result_row") as get_row_mock:
            view.get_result_rows(object_list)
            get_row_mock.assert_has_calls([call("foo"), call("bar")])

    def test_get_result_rows_applies_overview_annotations(self):
        """
        Assert that get_results_rows has the overview annotations applied to the
        object list.
        """
        view = self.get_view(self.get_request())
        with patch.object(view, "get_result_row"):
            with patch.object(self.queryset, "overview") as overview_mock:
                view.get_result_rows(self.queryset)
                overview_mock.assert_called()

    def test_get_result_row(self):
        """Assert that get_result_row returns the expected list of values."""
        view = self.get_view(self.get_request())
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            "Zepp",
            "Jimmy Page, Robert Plant",
            "United Kingdom",
            "This field cannot be sorted against.",
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_result_row_no_value(self):
        """Assert that get_result_row replaces empty values."""
        obj = self.model.objects.create(name="Black Sabbath")  # make would add an alias
        obj = self.get_annotated_model_obj(obj)
        view = self.get_view(self.get_request())
        view.empty_value_display = "//"
        expected = [
            f'<a href="{self.change_path.format(pk=obj.pk)}">Black Sabbath</a>',
            "//",
            "-",  # values is from a dbentry.utils.query.string_list annotation which sets empty value as '-'
            "//",
            "This field cannot be sorted against.",
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_get_result_row_link(self):
        """Assert that links to the object are added correctly."""
        view = self.get_view(self.get_request(), list_display_links=["name", "alias"])
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Zepp</a>',
            "Jimmy Page, Robert Plant",
            "United Kingdom",
            "This field cannot be sorted against.",
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_result_row_no_links(self):
        """
        Assert that no links to the object are added if list_display_links is
        None.
        """
        view = self.get_view(self.get_request(), list_display_links=None)
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            "Led Zeppelin",
            "Zepp",
            "Jimmy Page, Robert Plant",
            "United Kingdom",
            "This field cannot be sorted against.",
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_result_row_link_no_change_permission(self):
        """No link should be displayed if the user does not have view permission."""
        request = self.get_request(user=self.noperms_user)
        view = self.get_view(request, list_display_links=["name"])
        obj = self.get_annotated_model_obj(self.obj)
        self.assertNotIn('<a href="', view.get_result_row(obj)[0])

    def test_get_result_row_link_no_change_view(self):
        """No link should be displayed if the change view does not exist."""
        view = self.get_view(self.get_request(), list_display_links=["name"])
        obj = self.get_annotated_model_obj(self.obj)
        urlpatterns = URLConf.urlpatterns.copy()
        urlpatterns.pop(1)
        with patch.object(URLConf, "urlpatterns", new=urlpatterns):
            with override_settings(ROOT_URLCONF=URLConf):
                self.assertNotIn('<a href="', view.get_result_row(obj)[0])

    @expectedFailure
    def test_get_result_row_link_contains_preserved_filters(self):
        """
        The change page links in a row should contain the changelist request
        parameters.
        """
        # NOTE: why? what's the benefit of this?
        request = self.get_request(data={"p": ["1"]})
        view = self.get_view(request)
        obj = self.get_annotated_model_obj(self.obj)
        self.assertIn("p=1", view.get_result_row(obj)[0])

    def test_get_result_row_no_list_display(self):
        """
        The result row should be the __str__ representation of the result if no
        list_display items are set.
        """
        view = self.get_view(self.get_request(), list_display_links=None)
        with patch.object(view, "list_display", new=[]):
            with patch.object(self.model, "__str__") as str_mock:
                str_mock.return_value = "Foo Bar"
                self.assertEqual(view.get_result_row(self.obj), ["Foo Bar"])

    def test_get_query_string_add_params(self):
        """Assert that get_query_string adds query string parameters."""
        request = self.get_request(data={"o": ["1"]})
        view = self.get_view(request)
        self.assertEqual(view.get_query_string(new_params={"p": "2"}), "?o=1&p=2")

    def test_get_query_string_remove_params(self):
        """Assert that get_query_string removes query string parameters."""
        request = self.get_request(data={"o": ["1"], "q": ["Beep"]})
        view = self.get_view(request)
        self.assertEqual(view.get_query_string(remove=["o"]), "?q=Beep")

    def test_get_query_string_remove_params_empty_value(self):
        """
        Assert that get_query_string removes query string parameters if their
        value is set to an 'empty' value.
        """
        request = self.get_request(data={"o": ["1"], "q": ["Beep"]})
        view = self.get_view(request)
        self.assertEqual(view.get_query_string(new_params={"o": None}), "?q=Beep")

    def test_get_ordering_field(self):
        """
        Assert that get_ordering_field resolves the given field name to either
        a model field name or an order_field as defined on a view method.
        """
        test_data = [("name", "name"), ("members", "members_list"), ("foo", None)]
        view = self.get_view(self.get_request())
        for name, expected in test_data:
            with self.subTest(name=name):
                self.assertEqual(view.get_ordering_field(name), expected)

    def test_get_context_data(self):
        """Assert that get_context_data adds the expected items."""
        view = self.get_view(self.get_request())
        view.object_list = view.get_queryset().order_by("id")
        context = view.get_context_data()
        for context_item in ["page_range", "cl", "result_headers", "result_rows"]:
            with self.subTest(context_item=context_item):
                self.assertIn(context_item, context)

    def test_order_queryset_order_unfiltered_results_filtered(self):
        """
        Assert that order_queryset applies extended ordering when the queryset
        is filtered and order_unfiltered_results is False.
        """
        view = self.get_view(self.get_request())
        view.order_unfiltered_results = False
        view.ordering = ["name"]
        queryset = self.queryset.filter(id=1).order_by("alias")
        queryset = view.order_queryset(queryset)
        self.assertCountEqual(queryset.query.order_by, ["name", "alias", "id"])

    def test_order_queryset_order_unfiltered_results_unfiltered(self):
        """
        Assert that order_queryset does not apply extended ordering when the
        queryset is unfiltered and order_unfiltered_results is False.
        """
        view = self.get_view(self.get_request())
        view.order_unfiltered_results = False
        view.ordering = ["name"]
        queryset = self.queryset.order_by("alias")
        queryset = view.order_queryset(queryset)
        self.assertCountEqual(queryset.query.order_by, ["id"])

    def test_order_queryset_order_unfiltered_results_true(self):
        """
        Assert that order_queryset applies extended ordering regardless of
        whether the queryset is filtered when order_unfiltered_results is True.
        """
        view = self.get_view(self.get_request())
        view.order_unfiltered_results = True
        view.ordering = ["name"]
        for is_filtered in (True, False):
            queryset = self.queryset.order_by("alias")
            if is_filtered:
                queryset = queryset.filter(id=1)
            with self.subTest(is_filtered=is_filtered):
                queryset = view.order_queryset(queryset)
                self.assertCountEqual(queryset.query.order_by, ["name", "alias", "id"])

    def test_get_default_ordering_no_ordering(self):
        """
        Assert that get_default_ordering returns an empty list if no ordering is
        defined on either the view or the model.
        """
        view = self.get_view(self.get_request())
        self.assertEqual(view._get_default_ordering(), [])

    def test_get_default_ordering_view_ordering(self):
        """
        Assert that get_default_ordering returns the ordering defined on the
        view.
        """
        view = self.get_view(self.get_request())
        view.ordering = ["foo", "bar"]
        with patch.object(view.opts, "ordering", new=["model_foo", "model_bar"]):
            self.assertEqual(view._get_default_ordering(), ["foo", "bar"])

    def test_get_default_ordering_model_ordering(self):
        """
        Assert that get_default_ordering returns the ordering defined on the
        model if no ordering is specified on the view.
        """
        view = self.get_view(self.get_request())
        view.ordering = None
        with patch.object(view.opts, "ordering", new=["model_foo", "model_bar"]):
            self.assertEqual(view._get_default_ordering(), ["model_foo", "model_bar"])

    def test_get_ordering_fields_adds_default_ordering(self):
        """Assert that get_ordering_fields includes the default ordering."""
        view = self.get_view(self.get_request())
        with patch.object(view, "_get_default_ordering") as default_ordering_mock:
            default_ordering_mock.return_value = ["foo"]
            self.assertIn("foo", view.get_ordering_fields(self.queryset))

    def test_get_ordering_fields_adds_queryset_ordering(self):
        """Assert that get_ordering_fields includes the queryset ordering."""
        view = self.get_view(self.get_request())
        queryset = self.queryset.order_by("alias")
        with patch.object(view, "_get_default_ordering") as default_ordering_mock:
            default_ordering_mock.return_value = []
            self.assertIn("alias", view.get_ordering_fields(queryset))

    def test_get_ordering_fields_adds_id_field(self):
        """
        Assert that get_ordering_fields always includes an ordering field for
        the 'id' field.
        """
        view = self.get_view(self.get_request())
        queryset = self.queryset.order_by()
        with patch.object(view, "_get_default_ordering") as default_ordering_mock:
            default_ordering_mock.return_value = []
            self.assertIn("id", view.get_ordering_fields(queryset))

    def test_get_ordering_fields_prioritize_search_ordering(self):
        """
        Assert that get_ordering_fields returns just the ordering set on the
        queryset if prioritize_search_ordering is True.
        """
        view = self.get_view(self.get_request(data={SEARCH_VAR: "q"}))
        view.prioritize_search_ordering = True
        queryset = self.queryset.order_by("-id", "-name")
        self.assertEqual(view.get_ordering_fields(queryset), ("-id", "-name"))

    def test_get_search_results(self):
        """
        Assert that get_search_results calls queryset.search() if a search term
        is given.
        """
        for search_term in ("", "q"):
            with self.subTest(search_term=search_term):
                view = self.get_view(self.get_request(data={SEARCH_VAR: search_term}))
                with patch.object(self.queryset, "search") as search_mock:
                    view.get_search_results(self.queryset)
                    if search_term:
                        search_mock.assert_called()
                    else:
                        search_mock.assert_not_called()
                search_mock.reset_mock()

    def test_get_search_results_keeps_user_order(self):
        """
        Assert that get_search_results calls queryset.search() with ranked=False
        if the ORDER_VAR is present in the request.
        """
        for has_order_var in (True, False):
            with self.subTest(has_order_var=has_order_var):
                request_data = {SEARCH_VAR: "q"}
                if has_order_var:
                    request_data[ORDER_VAR] = "1"
                view = self.get_view(self.get_request(data=request_data))
                with patch.object(self.queryset, "search") as search_mock:
                    view.get_search_results(self.queryset)
                    search_mock.assert_called()
                    _args, kwargs = search_mock.call_args
                    if has_order_var:
                        self.assertFalse(kwargs["ranked"])
                    else:
                        self.assertTrue(kwargs["ranked"])
