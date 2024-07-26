"""Tests for the dbentry.site base views."""

import re
from unittest.mock import patch, Mock, call
from urllib.parse import urlencode, unquote

from django import forms
from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse
from django.template import TemplateDoesNotExist
from django.test import override_settings, TestCase
from django.urls import path, reverse, NoReverseMatch
from mizdb_tomselect.views import IS_POPUP_VAR

from dbentry.site.forms import InlineForm
from dbentry.site.views.base import (
    BaseEditView,
    Inline,
    BaseListView,
    SEARCH_VAR,
    ORDER_VAR,
    BaseViewMixin,
    ModelViewMixin,
    ACTION_SELECTED_ITEM,
    SearchableListView,
)
from dbentry.site.views.delete import DeleteView, DeleteSelectedView
from dbentry.site.views.help import HelpView, has_help_page
from dbentry.site.views.history import HistoryView
from tests.case import ViewTestCase, DataTestCase
from tests.model_factory import make
from .models import Band, Genre, Musician, Country


class BandView(BaseEditView):
    class GenreInline(Inline):
        model = Band.genres.through
        verbose_model = Genre

    model = Band
    form = forms.modelform_factory(Band, fields=forms.ALL_FIELDS)
    inlines = [GenreInline]
    require_confirmation = True


class BandListView(BaseListView):
    model = Band

    list_display = ["name", "alias", "members", "origin", "unsortable"]

    # @formatter:off
    def members(self, obj):
        return obj.members_list

    members.description = "Members"
    members.ordering = "-members_list"

    def unsortable(self, obj):
        return "This field cannot be sorted against."

    unsortable.description = "Ignore This"
    # @formatter:on

    def some_method(self, obj):
        pass


class BandHistoryView(HistoryView):
    model = Band


class CountryDeleteView(DeleteView):
    model = Country


class CountryListView(BaseListView):
    model = Country


class GenreListView(BaseListView):
    model = Genre


class MusicianListView(SearchableListView):
    model = Musician
    search_form_kwargs = {"fields": ["band", "origin__isnull"]}


admin_site = admin.AdminSite()


@admin.register(Band, site=admin_site)
class AdminView(admin.ModelAdmin):
    pass


def dummy_view(request):
    return HttpResponse("dummy")


class URLConf:
    urlpatterns = [
        path("band/", BandListView.as_view(), name="test_site_band_changelist"),
        path("band/add/", BandView.as_view(extra_context={"add": True}), name="test_site_band_add"),
        path(
            "band/<path:object_id>/change/",
            BandView.as_view(extra_context={"add": False}),
            name="test_site_band_change",
        ),
        path(
            "band/<path:object_id>/view/",
            BandView.as_view(extra_context={"add": False, "view_only": True}),
            name="test_site_band_view",
        ),
        path("<path:object_id>/history/", BandHistoryView.as_view(), name="test_site_band_history"),
        path("country/", CountryListView.as_view(), name="test_site_country_changelist"),
        path("country/<path:object_id>/delete/", CountryDeleteView.as_view(), name="test_site_country_delete"),
        path("country/<path:object_id>/view/", dummy_view, name="test_site_country_view"),
        path("genre/", GenreListView.as_view(), name="test_site_genre_changelist"),
        path("genre/<path:object_id>/view/", dummy_view, name="test_site_genre_view"),
        path("musician/", MusicianListView.as_view(), name="test_site_musician_changelist"),
        path("admin/", admin_site.urls),
        path("genre/<path:object_id>/view/", dummy_view, name="test_site_genre_view"),
        # Other URLs required by templates:
        *[
            path("", dummy_view, name=name)
            for name in ("index", "site_search", "searchbar_search", "password_change", "logout")
        ],
        path("help/index/", dummy_view, name="help_index"),
        path("help/<path:page_name>/", dummy_view, name="help"),
    ]
    app_name = "test_site"


@override_settings(ROOT_URLCONF=URLConf)
class TestBaseViewMixin(ViewTestCase):
    def test_get_admin_url(self):
        """
        Assert that get_admin_url returns the URL to the corresponding admin
        page.
        """
        request = self.get_response(reverse("test_site_band_changelist")).wsgi_request
        view = BaseViewMixin()
        self.assertEqual(view._get_admin_url(request), reverse("admin:test_site_band_changelist"))

    def test_get_admin_url_no_admin(self):
        """
        Assert that get_admin_irl returns the URL to the index if no
        corresponding admin page exists for the given request.
        """
        request = self.get_response(reverse("test_site_genre_changelist")).wsgi_request
        view = BaseViewMixin()
        self.assertEqual(view._get_admin_url(request), reverse("admin:index"))


@override_settings(ROOT_URLCONF=URLConf)
class TestModelViewMixin(ViewTestCase):
    view_class = ModelViewMixin

    def get_view(self, request=None, args=None, kwargs=None, **initkwargs):
        self.view_class.model = Band
        self.view_class.request = request
        return self.view_class()

    def test_get_preserved_filters_no_match(self):
        """
        Assert that get_preserved_filters returns an empty string if the
        requested URL could not be resolved.
        """
        view = self.get_view()
        request = self.get_request("foo/bar")
        self.assertEqual(view.get_preserved_filters(request), "")

    def test_get_preserved_filters_no_filters(self):
        """
        Assert that get_preserved_filters returns an empty string if no
        changelist filters have been preserved.
        """
        view = self.get_view()
        request = self.get_response(reverse("test_site_band_changelist")).wsgi_request
        self.assertEqual(view.get_preserved_filters(request), "")

    def test_get_preserved_filters_changelist(self):
        """
        Assert that get_preserved_filters uses the encoded request data as
        preserved filters if the request is for the changelist.
        """
        view = self.get_view()
        request = self.get_response(reverse("test_site_band_changelist"), data={"foo": "bar"}).wsgi_request
        self.assertEqual(view.get_preserved_filters(request), "_changelist_filters=foo%3Dbar")

    def test_get_preserved_filters_not_changelist(self):
        """
        Assert that get_preserved_filters uses the query string parameter
        "_changelist_filters" as preserved_filters if the request is not for
        the changelist.
        """
        view = self.get_view()
        request = self.get_response(reverse("test_site_band_add"), data={"_changelist_filters": "foo=bar"}).wsgi_request
        self.assertEqual(view.get_preserved_filters(request), "_changelist_filters=foo%3Dbar")

    def test_get_context_data_adds_help_url(self):
        """
        Assert that get_context_data overrides the 'help_url' context item if a
        help page for the given model exists.
        """
        view = self.get_view(request=self.get_request())
        with patch.object(view, "_get_admin_url"):
            for help_page_exists in (True, False):
                with self.subTest(help_page_exists=help_page_exists):
                    with patch("dbentry.site.views.help.has_help_page") as has_help_page_mock:
                        has_help_page_mock.return_value = help_page_exists
                        context = view.get_context_data()
                    if help_page_exists:
                        self.assertEqual(context["help_url"], "/help/band/")
                    else:
                        self.assertEqual(context["help_url"], "/help/index/")


@override_settings(ROOT_URLCONF=URLConf)
class TestBaseEditView(DataTestCase, ViewTestCase):
    model = Band
    view_class = BandView

    @classmethod
    def setUpTestData(cls):
        cls.origin = origin = make(Country, name="Denmark")
        cls.rock, cls.spam = genres = [make(Genre, genre="Rock"), make(Genre, genre="Spam")]
        cls.obj = make(
            Band,
            name="Vikings of SPAM",
            url="www.lovely-spam.com",
            origin=origin,
            genres=genres,
            musician__extra=1,
        )
        super().setUpTestData()

    def setUp(self):
        super().setUp()
        self.url = reverse("test_site_band_change", kwargs={"object_id": self.obj.pk})

    def get_view(self, request=None, args=None, kwargs=None, add=False, **initkwargs):
        initkwargs["extra_context"] = {"add": add}
        return super().get_view(request, args, kwargs, **initkwargs)

    def test_get_permission_required_add(self):
        """
        Assert that get_permission_required returns the 'add' permission if the
        view is an 'add' view.
        """
        view = self.get_view(add=True)
        self.assertEqual(view.get_permission_required(), ["test_site.add_band"])

    def test_get_permission_required_change(self):
        """
        Assert that get_permission_required returns the 'change' permission if
        the view is ae 'change' view.
        """
        view = self.get_view(add=False)
        self.assertEqual(view.get_permission_required(), ["test_site.change_band"])

    def test_get_success_url_add_another(self):
        """
        Assert that get_success_url returns the URL for the add page if
        '_addanother' is in the request data.
        """
        view = self.get_view(self.post_request(data={"_addanother": ""}))
        self.assertEqual(view.get_success_url(), reverse("test_site_band_add"))

    def test_get_success_url_continue(self):
        """
        Assert that get_success_url returns the URL for the change page if
        '_continue' is in the request data.
        """
        view = self.get_view(self.post_request(data={"_continue": ""}), kwargs={"pk": self.obj.pk})
        view.object = self.obj
        self.assertEqual(view.get_success_url(), reverse("test_site_band_change", args=[self.obj.pk]))

    def test_get_success_url_changelist(self):
        """Assert that get_success_url returns the URL for the changelist page."""
        view = self.get_view(self.post_request())
        self.assertEqual(view.get_success_url(), reverse("test_site_band_changelist"))

    def test_get_success_url_popup(self):
        """
        Assert that get_success_url returns an empty string if the IS_POPUP_VAR
        is in the query parameters.
        """
        # Mock mizdb-tomselect.IS_POPUP_VAR
        with patch("dbentry.site.views.base.IS_POPUP_VAR", new="FOO") as popup_var_mock:
            view = self.get_view(self.get_request("/", data={popup_var_mock: 1}))
            self.assertEqual(view.get_success_url(), "")

    def test_get_changelist_links(self):
        view = self.get_view(self.get_request(), add=False)
        view.object = self.obj
        links = view.get_changelist_links()
        self.assertIn((f"/musician/?band={self.obj.pk}", "Musicians", 1), links)

    def test_get_changelist_links_ignores_relations_with_inlines(self):
        """No changelist_links should be created for relations handled by inlines."""
        view = self.get_view(self.get_request(), add=False)
        view.object = self.obj
        links = view.get_changelist_links()
        self.assertNotIn((f"/genre/?band={self.obj.pk}", "Genres", 1), links)

    def test_get_changelist_links_prefer_labels_arg(self):
        """Passed in labels should be used over the model's verbose name."""
        view = self.get_view(self.get_request(), add=False)
        view.object = self.obj
        links = view.get_changelist_links(labels={"musician": "Hovercrafts"})
        self.assertIn((f"/musician/?band={self.obj.pk}", "Hovercrafts", 1), links)

    def test_get_changelist_links_uses_related_name(self):
        """If the relation has a related_name, it should be used as the label."""
        rel = Musician._meta.get_field("band").remote_field
        with patch.object(rel, "related_name", new="hovercrafts_full_of_eels"):
            view = self.get_view(self.get_request(), add=False)
            view.object = self.obj
            links = view.get_changelist_links()
            self.assertIn((f"/musician/?band={self.obj.pk}", "Hovercrafts Full Of Eels", 1), links)

    def test_initial_adds_preserved_filters(self):
        """
        Assert that values from preserved changelist filters are added to the
        form's initial data.
        """
        filters = {"q": "Foo"}
        request = self.get_request("", data={"_changelist_filters": urlencode(filters)})
        view = self.get_view(request)
        initial = view.get_initial()
        self.assertIn("q", initial)
        self.assertEqual(initial["q"], filters["q"])

    def test_confirmation_required(self):
        """Changes that are big enough should require confirmation."""
        form_data = {
            "name": "Hovercrafts Full Of Eels",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        response = self.post_response(self.url, data=form_data, follow=True)
        self.assertTemplateUsed(response, "mizdb/change_confirmation.html")
        self.assertNotEqual(
            self.obj.name,
            "Hovercrafts Full Of Eels",
            msg="The object should not be changed without confirmation.",
        )

    def test_confirmation_not_required(self):
        """Changes that are minor enough should not require confirmation."""
        form_data = {
            "name": "Vikings of SPAMs",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        response = self.post_response(self.url, data=form_data, follow=True)
        self.assertTemplateUsed(response, "mizdb/change_form.html")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "Vikings of SPAMs")

    def test_change_confirmed(self):
        """Assert the changes go through if the user has confirmed them."""
        form_data = {
            "name": "Hovercrafts Full Of Eels",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        session = self.client.session
        session["confirmed_form_data"] = form_data
        session.save()
        response = self.post_response(
            self.url,
            data={"_change_confirmed": "True", **form_data},
            follow=True,
        )
        self.assertTemplateUsed(response, "mizdb/change_form.html")
        self.obj.refresh_from_db()
        self.assertEqual(self.obj.name, "Hovercrafts Full Of Eels")

    def test_post_save_adds_logentry(self):
        """
        Assert that a LogEntry object is created after saving the model object.
        """
        form_data = {
            "name": "Vikings of SPAMs",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        self.post_response(self.url, data=form_data)
        ct = ContentType.objects.get_for_model(self.model)
        self.assertTrue(LogEntry.objects.filter(object_id=self.obj.pk, content_type=ct).exists())

    def test_log_entry_change_message(self):
        """
        Assert that the LogEntry change message mentions the field(s) that were
        changed.
        """
        form_data = {
            "name": "Vikings of SPAMs",
            "url": "www.egg-sausages-bacon.com",
            "origin_id": "",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        self.post_response(self.url, data=form_data)
        ct = ContentType.objects.get_for_model(self.model)
        entry = LogEntry.objects.get(object_id=self.obj.pk, content_type=ct)
        self.assertEqual("Name, Url und Origin Country geändert.", entry.get_change_message())

    def test_get_success_message_add(self):
        """Assert that a message is displayed when an object was added successfully."""
        form_data = {
            "name": "Vikings of SPAMs",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        response = self.post_response(reverse("test_site_band_add"), data=form_data)
        self.assertMessageSent(response.wsgi_request, re.compile("Band.*Vikings of SPAMs.*erfolgreich erstellt."))

    def test_get_success_message_change(self):
        """Assert that a message is displayed when an object was changed successfully."""
        form_data = {
            "name": "Vikings of SPAMs",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        response = self.post_response(self.url, data=form_data)
        self.assertMessageSent(response.wsgi_request, re.compile(r"Band.*Vikings of SPAM.*erfolgreich geändert"))

    def test_no_success_message_when_confirming_changes(self):
        """Assert that no user message is displayed when confirming a change."""
        form_data = {
            "name": "Hovercrafts Full Of Eels",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
        }
        response = self.post_response(self.url, data=form_data, follow=True)
        self.assertMessageNotSent(
            response.wsgi_request, re.compile("Band.*Hovercrafts Full Of Eels.*erfolgreich geändert.")
        )

    def test_success_message_after_confirming_changes(self):
        """Assert that a user message is displayed after confirming a change."""
        form_data = {
            "name": "Hovercrafts Full Of Eels",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
            "_change_confirmed": "True",
        }
        response = self.post_response(self.url, data=form_data, follow=True)
        self.assertMessageSent(
            response.wsgi_request, re.compile("Band.*Hovercrafts Full Of Eels.*erfolgreich geändert.")
        )

    def test_get_success_message_popup(self):
        """Assert that no user message is issued when the view is a popup."""
        form_data = {
            "name": "Vikings of SPAMs",
            "_continue": "",
            "Band_genres-TOTAL_FORMS": "0",
            "Band_genres-INITIAL_FORMS": "0",
            IS_POPUP_VAR: "1",
        }
        response = self.post_response(reverse("test_site_band_add"), data=form_data)
        self.assertMessageNotSent(response.wsgi_request, re.compile("Band.*Vikings of SPAMs.*erfolgreich erstellt."))

    def test_does_not_exist_user_message(self):
        """
        Assert that the user is redirect to the changelist with a message if the
        requested object does not exist.
        """
        response = self.get_response(reverse("test_site_band_change", args=[-1]), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.view_name, "test_site_band_changelist")
        self.assertMessageSent(response.wsgi_request, "Band mit ID '-1' existiert nicht. Vielleicht gelöscht")

    def test_view_only(self):
        """Assert that the 'view_only' response contains the expected context."""
        url = reverse("test_site_band_view", kwargs={"object_id": self.obj.pk})
        response = self.get_response(url, user=self.super_user)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mizdb/viewonly.html")
        expected = [
            ("Name", "Vikings of SPAM"),
            ("Band Alias", "---"),
            ("Url", '<a href="www.lovely-spam.com" target="_blank">www.lovely-spam.com</a>'),
            ("Origin Country", f'<a href="/country/{self.origin.pk}/view/" target="_blank">Denmark</a>'),
            (
                "Genres",
                f'<a href="/genre/{self.rock.pk}/view/" target="_blank">Rock</a>\n'
                f'<a href="/genre/{self.spam.pk}/view/" target="_blank">Spam</a>\n',
            ),
        ]
        object_data = response.context["data"]
        for name, value in expected:
            with self.subTest(field=name):
                self.assertEqual(object_data[name], value)


@override_settings(ROOT_URLCONF=URLConf)
class TestBaseListView(DataTestCase, ViewTestCase):
    model = Band
    view_class = BandListView
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
        cls.origin = make(Country, name="United Kingdom")
        cls.obj = make(cls.model, name="Led Zeppelin", alias="Zepp", origin=cls.origin)  # noqa
        cls.jimmy = make(Musician, name="Jimmy Page", band=cls.obj)  # noqa
        cls.robert = make(Musician, name="Robert Plant", band=cls.obj)  # noqa

    def setUp(self):
        super().setUp()
        self.url = reverse("test_site_band_changelist")

    def get_annotated_model_obj(self, obj):
        """Apply the view's changelist annotations to the given object."""
        return self.queryset.overview().filter(pk=obj.pk).get()

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

        expected_labels = ["Name", "Band Alias", "Members", "Origin Country", "Ignore This"]
        for i, expected_label in enumerate(expected_labels):
            with self.subTest(index=i, label=expected_label):
                self.assertEqual(headers[i]["text"], expected_label)

    def test_get_result_headers_field_not_in_sortable_by(self):
        """
        Assert that a header is flagged as not sortable if the field is not
        included in the view's ``sortable_by``.
        """
        view = self.get_view(self.get_request())
        view.sortable_by = ["name"]
        headers = view.get_result_headers()
        self.assertFalse(headers[1].get("sortable", False))
        self.assertTrue(headers[0].get("sortable", False))  # name should still be sortable

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

    def test_get_queryset_applies_overview_annotations(self):
        """Assert that get_queryset applies the overview annotations."""
        view = self.get_view(self.get_request())
        self.assertIn("members_list", view.get_queryset().query.annotations)

    def test_get_result_row(self):
        """Assert that get_result_row returns the expected list of values."""
        view = self.get_view(self.get_request())
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            f'<a class="change-link" href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            "Zepp",
            "Jimmy Page, Robert Plant",
            "United Kingdom",
            "This field cannot be sorted against.",
        ]
        row = view.get_result_row(obj)
        self.assertHTMLEqual(row[0], expected[0])
        self.assertEqual(row[1:], expected[1:])

    def test_get_result_row_no_value(self):
        """Assert that get_result_row replaces empty values."""
        obj = self.model.objects.create(name="Black Sabbath")  # make would add an alias
        obj = self.get_annotated_model_obj(obj)
        view = self.get_view(self.get_request())
        view.empty_value_display = "//"
        expected = [
            f'<a  class="change-link" href="{self.change_path.format(pk=obj.pk)}">Black Sabbath</a>',
            "//",
            "-",  # values is from a dbentry.utils.query.string_list annotation which sets empty value as '-'
            "//",
            "This field cannot be sorted against.",
        ]
        row = view.get_result_row(obj)
        self.assertHTMLEqual(row[0], expected[0])
        self.assertEqual(row[1:], expected[1:])

    def test_get_get_result_row_link(self):
        """Assert that links to the object are added correctly."""
        list_display_links = ["name", "alias"]
        view = self.get_view(self.get_request(), list_display_links=["name", "alias"])
        obj = self.get_annotated_model_obj(self.obj)
        expected = {
            "name": f'<a class="change-link" href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            "alias": f'<a class="change-link" href="{self.change_path.format(pk=self.obj.pk)}">Zepp</a>',
        }
        row = view.get_result_row(obj)
        for list_display_link in list_display_links:
            with self.subTest(list_display_link=list_display_link):
                self.assertHTMLEqual(
                    row[self.view_class.list_display.index(list_display_link)], expected[list_display_link]
                )

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

    @override_settings(ANONYMOUS_CAN_VIEW=False)
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
        # Remove the change view from the available URL patterns.
        urlpatterns = URLConf.urlpatterns.copy()
        for i, pattern in enumerate(URLConf.urlpatterns):
            if pattern.name == "test_site_band_change":
                urlpatterns.pop(i)
                break
        with patch.object(URLConf, "urlpatterns", new=urlpatterns):
            with override_settings(ROOT_URLCONF=URLConf):
                self.assertNotIn('<a href="', view.get_result_row(obj)[0])

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
        test_data = [("name", "name"), ("members", "-members_list"), ("foo", None)]
        view = self.get_view(self.get_request())
        for name, expected in test_data:
            with self.subTest(name=name):
                self.assertEqual(view.get_ordering_field(name), expected)

    def test_get_context_data(self):
        """Assert that get_context_data adds the expected items."""
        request = self.get_response(reverse("test_site_band_changelist")).wsgi_request
        view = self.get_view(request)
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

    def test_order_queryset_ORDER_VAR(self):
        """
        Assert that order_queryset applies the ordering given by the ORDER_VAR
        query parameter.
        """
        # ORDER_VAR uses the column number of list_display items:
        # - 0 is the name column
        # - 1 is the alias column
        # - 2 is the members column with ordering field: -members_list (DESC)
        # - 4 is the unsortable column without an ordering field
        # "name" should be DESC, "alias" should be ASC, "members_list" should be
        # ASC (reverse of its default DESC), and "unsortable" should be ignored
        # since it has no ordering field.
        view = self.get_view(self.get_request("", data={ORDER_VAR: "4.-2.1.-0"}))
        queryset = view.order_queryset(self.queryset.overview().order_by("name", "alias", "members_list"))
        self.assertCountEqual(queryset.query.order_by, ["members_list", "alias", "-name"])

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

    def test_get_queryset_applies_search(self):
        """
        Assert that the queryset returned by get_queryset has search filters
        applied to it.
        """
        view = self.get_view(self.get_request("", data={SEARCH_VAR: "Foo"}))
        queryset = view.get_queryset()
        self.assertTrue(queryset.query.has_filters())
        view = self.get_view(self.get_request("", data={}))
        queryset = view.get_queryset()
        self.assertFalse(queryset.query.has_filters())

    def test_get_queryset_adds_annotations(self):
        """
        Assert that the queryset returned by get_queryset has list display
        annotations applied to it.
        """
        view = self.get_view(self.get_request())
        queryset = view.get_queryset()
        self.assertIn("members_list", queryset.query.annotations)

    def test_get_queryset_adds_ordering(self):
        """
        Assert that the queryset returned by get_queryset has ordering applied
        to it.
        """
        view = self.get_view(self.get_request())
        queryset = view.get_queryset()
        self.assertTrue(queryset.query.order_by)

    def test_get_ordering_field_columns_order_var(self):
        view = self.get_view(self.get_request("", data={ORDER_VAR: "0.-1.2"}))
        self.assertEqual(view.get_ordering_field_columns(), {0: "asc", 1: "desc", 2: "asc"})

    def test_get_ordering_field_columns_no_order_var(self):
        view = self.get_view(self.get_request(""))
        view.ordering = ["-name", "alias", "members_list"]
        self.assertEqual(view.get_ordering_field_columns(), {0: "desc", 1: "asc", 2: "asc"})

    def test_post_unknown_action(self):
        """Assert that a user message is issued if an unknown action was selected."""
        response = self.post_response(self.url, data={"action_name": "foo", ACTION_SELECTED_ITEM: [self.obj.pk]})
        self.assertMessageSent(response.wsgi_request, "Abgebrochen")
        self.assertRedirects(response, self.url)

    def test_post_no_objects_selected(self):
        """
        Assert that a user message is issued if action was requested but no
        objects were selected.
        """
        response = self.post_response(self.url, data={"action_name": "delete"})
        self.assertMessageSent(response.wsgi_request, "Abgebrochen")
        self.assertRedirects(response, self.url)


@override_settings(ROOT_URLCONF=URLConf)
class TestDeleteView(ViewTestCase):
    model = Country
    view_class = CountryDeleteView

    @classmethod
    def setUpTestData(cls):
        cls.obj = obj = make(Country)
        cls.band = make(Band, origin=obj)
        super().setUpTestData()

    def setUp(self):
        self.url = reverse("test_site_country_delete", kwargs={"object_id": self.obj.pk})

    def test_requires_permission(self):
        """Assert that the user must have 'delete' permission to access the view."""
        response = self.get_response(self.url, user=self.staff_user, follow=True)
        self.assertEqual(response.status_code, 403)
        self.staff_user = self.add_permission(self.staff_user, "delete", self.model)
        response = self.get_response(self.url, user=self.staff_user, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_deletes(self):
        """Assert that a post request deletes the given object."""
        response = self.post_response(self.url, user=self.super_user)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.model.objects.filter(pk=self.obj.pk).exists())

    def test_redirects_to_changelist(self):
        """Assert that a successful deletion redirects the user to the model's changelist."""
        response = self.post_response(self.url, user=self.super_user, follow=True)
        self.assertEqual(response.wsgi_request.path, reverse("test_site_country_changelist"))

    def test_logs_deletion(self):
        """Assert that LogEntry objects are created for each deleted object."""
        self.post_response(self.url, user=self.super_user, follow=True)
        ct = ContentType.objects.get_for_model(self.model)
        self.assertTrue(LogEntry.objects.filter(object_id=self.obj.pk, content_type=ct).exists())
        # Deleted in the cascade:
        ct = ContentType.objects.get_for_model(Band)
        self.assertTrue(LogEntry.objects.filter(object_id=self.band.pk, content_type=ct).exists())


@override_settings(ROOT_URLCONF=URLConf)
class TestDeleteSelectedView(ViewTestCase):
    model = Band
    view_class = DeleteSelectedView

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(Band)
        cls.obj2 = make(Band)
        super().setUpTestData()

    def setUp(self):
        self.url = reverse("test_site_band_changelist")

    def post_data(self, confirmed=False):
        data = {"action_name": "delete", ACTION_SELECTED_ITEM: [str(self.obj1.pk), str(self.obj2.pk)]}
        if confirmed:
            data[self.view_class.action_confirmed_name] = "yes"
        return data

    def test_deletion_confirmed(self):
        """
        Assert that a confirmed deletion POST request redirects back to the
        changelist.
        """
        response = self.post_response(self.url, data=self.post_data(confirmed=True), user=self.super_user, follow=True)
        self.assertTemplateUsed(response, "mizdb/changelist.html")

    def test_deletion_success(self):
        """Assert that a successful deletion request deletes the items."""
        self.post_response(self.url, data=self.post_data(confirmed=True), user=self.super_user)
        self.assertFalse(Band.objects.filter(pk__in=[self.obj1.pk, self.obj2.pk]).exists())

    def test_deletion_confirmation_required(self):
        """
        Assert that an unconfirmed deletion POST request returns the
        confirmation page.
        """
        response = self.post_response(self.url, data=self.post_data(confirmed=False), user=self.super_user)
        self.assertTemplateUsed(response, "mizdb/delete_confirmation.html")


@override_settings(ROOT_URLCONF=URLConf)
class TestHistoryView(ViewTestCase):
    model = Band
    view_class = BandHistoryView

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Band)
        ct = ContentType.objects.get_for_model(cls.model)
        cls.obj_log1 = make(LogEntry, object_id=cls.obj.pk, content_type=ct)  # noqa
        cls.obj_log2 = make(LogEntry, object_id=cls.obj.pk, content_type=ct)  # noqa
        # Should not be included in the LogEntry queryset for `obj`.
        cls.other_log = make(LogEntry, object_id="-1", content_type=ct)
        super().setUpTestData()

    def setUp(self):
        self.url = reverse("test_site_band_history", kwargs={"object_id": self.obj.pk})

    @override_settings(ANONYMOUS_CAN_VIEW=False)
    def test_requires_permission(self):
        """Assert that the user must have 'view' permission to access the view."""
        response = self.get_response(self.url, user=self.staff_user, follow=True)
        self.assertEqual(response.status_code, 403)
        self.staff_user = self.add_permission(self.staff_user, "view", self.model)
        response = self.get_response(self.url, user=self.staff_user, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_get_queryset(self):
        """Assert that get_queryset returns the expected LogEntry queryset."""
        view = self.get_view(kwargs={"object_id": str(self.obj.pk)})
        self.assertQuerySetEqual(view.get_queryset(), [self.obj_log1, self.obj_log2])


@override_settings(ROOT_URLCONF=URLConf)
class TestSearchableListView(ViewTestCase):
    model = Musician
    view_class = MusicianListView

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.fighters = fighters = make(Band, name="Foo Fighters")
        cls.obj = make(cls.model, name="Foo Fighter", band=fighters)

    def test_get_search_results(self):
        """Assert that get_search_results returns the expected queryset result."""
        view = self.get_view(self.get_request(data={"band": self.fighters.pk}))
        self.assertIn(self.obj, view.get_search_results(self.model.objects))

    def test_get_filters(self):
        """Assert that get_filters returns the expected dictionary."""
        view = self.get_view()
        search_form = view.get_search_form(data={"band": self.fighters.pk})
        self.assertEqual(view.get_filters(search_form), {"band": self.fighters})

    def test_get_filters_in_lookup(self):
        """
        Assert that get_filters splits the value into a list if the lookup
        is '__in'.
        """
        view = self.get_view()
        search_form = view.get_search_form()
        with patch.object(search_form, "get_filters_params") as get_filters_params_mock:
            get_filters_params_mock.return_value = {"id__in": "1,42"}
            self.assertEqual(view.get_filters(search_form), {"id__in": ["1", "42"]})

    def test_get_filters_is_null_lookup(self):
        """
        Assert that get_filters transforms the value to a boolean if the lookup
        is '__isnull'.
        """
        view = self.get_view()
        search_form = view.get_search_form()
        with patch.object(search_form, "get_filters_params") as get_filters_params_mock:
            get_filters_params_mock.return_value = {"origin__isnull": "1"}
            self.assertEqual(view.get_filters(search_form), {"origin__isnull": True})

    def test_get_context_data(self):
        """
        Assert that get_context_data includes the empty search form fields in
        the 'collapsed' list, and the non-empty fields in the 'show' list.
        """

        class SearchForm(forms.Form):
            non_empty = forms.CharField(required=False)
            empty_bool = forms.BooleanField(required=False)
            empty_value = forms.CharField(required=False)
            empty_multi = forms.MultiValueField(required=False, fields=[forms.CharField()] * 2)

        search_form = SearchForm(
            data={
                "empty_bool": False,
                "empty_value": "",
                "empty_multi": [None, None],
                "non_empty": "foo",
            }
        )
        view = self.get_view()
        with patch("dbentry.site.views.base.super") as super_mock:
            super_mock.return_value.get_context_data.return_value = {"advanced_search_form": search_form}
            ctx = view.get_context_data()
            self.assertEqual(
                ctx["collapsed_fields"], [search_form[f] for f in ("empty_bool", "empty_value", "empty_multi")]
            )
            self.assertEqual(ctx["shown_fields"], [search_form["non_empty"]])


class TestHelpView(ViewTestCase):
    view_class = HelpView

    def test_has_help_page(self):
        """
        Assert that has_help_page checks if a help page template with the given
        name exists.
        """
        with patch("dbentry.site.views.help.get_template") as get_template_mock:
            for has_page in (True, False):
                if not has_page:
                    get_template_mock.side_effect = TemplateDoesNotExist("Test")
                self.assertEqual(has_help_page("foo"), has_page)

    def test(self):
        """Assert that the GET response uses the expected help page template."""
        response = self.client.get(reverse("help", kwargs={"page_name": "artikel"}))
        self.assertTemplateUsed(response, "help/artikel.html")

    def test_help_page_does_not_exist(self):
        """
        Assert that a request for a help page that does not exist redirects to
        the help index.
        """
        response = self.client.get(reverse("help", kwargs={"page_name": "__foo__"}), follow=True)
        self.assertTemplateUsed(response, "help/index.html")

    @patch("dbentry.site.views.help.has_help_page", new=Mock(return_value=False))
    def test_sends_user_message_if_help_page_does_not_exist(self):
        """
        Assert that a messages is send if the requested help page does not
        exist.
        """
        response = self.client.get(reverse("help", kwargs={"page_name": "__foo__"}), follow=True)
        self.assertMessageSent(response.wsgi_request, "Hilfe Seite für '__foo__' nicht gefunden.")


@override_settings(ROOT_URLCONF=URLConf)
class TestInline(TestCase):
    class GenreInline(Inline):
        model = Band.genres.through
        verbose_model = Genre

    def test_get_name_verbose_name_set(self):
        with patch.object(self.GenreInline, "verbose_name", new="Foo"):
            inline = self.GenreInline(Band)
            self.assertEqual(inline._get_name("verbose_name"), "Foo")

    def test_get_name_verbose_name_plural_set(self):
        with patch.object(self.GenreInline, "verbose_name_plural", new="Foo Plural"):
            inline = self.GenreInline(Band)
            self.assertEqual(inline._get_name("verbose_name_plural"), "Foo Plural")

    def test_get_name_verbose_model_set(self):
        with patch.object(self.GenreInline, "verbose_model", new=Genre):
            inline = self.GenreInline(Band)
            self.assertEqual(inline._get_name("verbose_name"), Genre._meta.verbose_name)
            self.assertEqual(inline._get_name("verbose_name_plural"), Genre._meta.verbose_name_plural)

    def test_get_no_attr_or_verbose_model_set(self):
        with patch.object(self.GenreInline, "verbose_model", new=None):
            inline = self.GenreInline(Band)
            self.assertEqual(inline._get_name("verbose_name"), inline.model._meta.verbose_name)
            self.assertEqual(inline._get_name("verbose_name_plural"), inline.model._meta.verbose_name_plural)

    def test_init_sets_verbose_names(self):
        inline = self.GenreInline(Band)
        self.assertEqual(inline.verbose_name, Genre._meta.verbose_name)
        self.assertEqual(inline.verbose_name_plural, Genre._meta.verbose_name_plural)

    def test_get_formset_class(self):
        inline = self.GenreInline(Band)
        formset_class = inline.get_formset_class()
        self.assertEqual(formset_class.model, inline.model)
        self.assertEqual(formset_class.fk.related_model, Band)
        self.assertTrue(issubclass(formset_class.form, InlineForm))
        self.assertEqual(formset_class.extra, 1)

    def test_get_changelist_url_attr_set(self):
        """
        Assert that ``get_changelist_url`` returns the value of the
        `changelist_url` attribute if it is set.
        """
        inline = self.GenreInline(Band)
        inline.changelist_url = "foo"
        with patch.object(inline, "get_changelist_fk_field", Mock(return_value="genre")):
            self.assertEqual(inline.get_changelist_url(), "foo")

    def test_get_changelist_url_id_field_set(self):
        """
        Assert that ``get_changelist_url`` returns the expected URL if a
        changelist_fk_field could be found.
        """
        inline = self.GenreInline(Band)
        with patch.object(inline, "get_changelist_fk_field", Mock(return_value="genre")):
            self.assertEqual(inline.get_changelist_url(), "/genre/")

    def test_get_changelist_url_no_reverse_match(self):
        """
        Assert that ``get_changelist_url`` returns an empty string if the URL
        could not be reversed.
        """
        inline = self.GenreInline(Band)
        with patch.object(inline, "get_changelist_fk_field", Mock(return_value="genre")):
            with patch("dbentry.site.views.base.reverse") as reverse_mock:
                reverse_mock.side_effect = NoReverseMatch
                self.assertEqual(inline.get_changelist_url(), "")

    def test_get_changelist_url_field_is_none(self):
        """
        Assert that ``get_changelist_url`` returns an empty string if
        get_changelist_fk_field returns None.
        """
        inline = self.GenreInline(Band)
        with patch.object(inline, "get_changelist_fk_field", Mock(return_value=None)):
            self.assertEqual(inline.get_changelist_url(), "")

    def test_get_changelist_fk_field_none(self):
        """
        Assert that ``get_changelist_fk_field`` returns an empty string if
        changelist_fk_field is set to None.
        """
        inline = self.GenreInline(Band)
        inline.changelist_fk_field = None
        self.assertEqual(inline.get_changelist_fk_field(), "")

    def test_get_changelist_fk_field_attr_set(self):
        """
        Assert that ``get_changelist_fk_field`` returns the value of the
        changelist_fk_field attribute if it is set.
        """
        inline = self.GenreInline(Band)
        inline.changelist_fk_field = "foo"
        self.assertEqual(inline.get_changelist_fk_field(), "foo")

    def test_get_changelist_fk_field_more_than_three_fields(self):
        """
        Assert that ``get_changelist_fk_field`` returns an empty string if the
        inline model has more than three model fields.
        """
        inline = self.GenreInline(Band)
        with patch.object(inline.model._meta, "get_fields", Mock(return_value=[1, 2, 3, 4])):
            self.assertEqual(inline.get_changelist_fk_field(), "")

    def test_get_changelist_fk_field(self):
        """
        Assert that ``get_changelist_fk_field`` returns the name of the
        ForeignKey field to the target model.
        """
        inline = self.GenreInline(Band)
        self.assertEqual(inline.get_changelist_fk_field(), "genre")

    def test_get_context_data(self):
        inline = self.GenreInline(Band)
        expected = {
            "verbose_name": "Genre",
            "verbose_name_plural": "Genres",
            "model_name": "band_genres",
            "add_text": "Genre hinzufügen",
            "tabular": True,
            "changelist_url": "/genre/",
            "changelist_fk_field": "genre",
        }
        self.assertEqual(inline.get_context_data(), expected)
