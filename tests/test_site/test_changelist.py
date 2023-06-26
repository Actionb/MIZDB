from urllib.parse import unquote

from django.contrib.postgres.aggregates import ArrayAgg
from django.test import override_settings
from django.urls import reverse, path
from django.views import View

from dbentry.site.views.base import BaseListView
from tests.case import ViewTestCase, DataTestCase
from tests.model_factory import make
from tests.test_site.models import Band, Musician, Country


class ChangelistTestCase(DataTestCase, ViewTestCase):

    changelist_path = ''
    change_path = ''
    add_path = ''

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        opts = cls.model._meta
        url_name = f"{opts.app_label}_{opts.model_name}"
        if not cls.changelist_path:
            cls.changelist_path = reverse(url_name + '_changelist')
        if not cls.change_path:
            cls.change_path = unquote(reverse(url_name + '_change', args=['{pk}']))
        if not cls.add_path:
            cls.add_path = reverse(url_name + '_add')

    def get_annotated_model_obj(self, obj):
        """Apply the view's changelist annotations to the given object."""
        return self.queryset.overview().filter(pk=obj.pk).get()


class BandListView(BaseListView):
    model = Band

    list_display = ['name', 'alias', 'members', 'origin', 'unsortable']

    def members(self, obj):
        return obj.members_list
    members.short_description = 'Members'
    members.order_field = 'members_list'

    def unsortable(self, obj):
        return "This field cannot be sorted against."
    unsortable.short_description = "Ignore"

    def some_method(self, obj):
        pass


class URLConf:
    app_name = 'test_site'
    urlpatterns = [
        path('add/', View.as_view(), name='test_site_band_add'),
        path('<path:object_id>/change/', View.as_view(), name='test_site_band_change'),
        path('', BandListView.as_view(), name='test_site_band_changelist'),
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
        view = self.get_view(self.get_request())
        test_data = [
            # name, (expected attr and label)
            ("alias", (self.model._meta.get_field("alias"), "Alias")),  # model field
            ("unsortable", (view.unsortable, "Ignore")),  # method with a description
            ("some_method", (view.some_method, "Some method")),  # method without a description
            ("foo_bar", (None, "Foo bar")),  # can't resolve name
        ]
        for name, expected in test_data:
            with self.subTest(name=name):
                self.assertEqual(view._lookup_field(name), expected)

    def test_get_result_headers(self):
        headers = self.get_view(self.get_request()).get_result_headers()
        self.assertEqual(
            headers,
            [
                {"text": "Name"},
                {"text": "Alias"},
                {"text": "Members"},
                {"text": "Origin country"},
                {"text": "Ignore"}
            ]
        )

    def test_get_result_row(self):
        view = self.get_view(self.get_request())
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            'Zepp',
            'Jimmy Page, Robert Plant',
            "United Kingdom",
            "This field cannot be sorted against."
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_result_row_no_value(self):
        obj = self.model.objects.create(name="Black Sabbath")  # make would add an alias
        obj = self.get_annotated_model_obj(obj)
        view = self.get_view(self.get_request())
        expected = [
            f'<a href="{self.change_path.format(pk=obj.pk)}">Black Sabbath</a>',
            '-',
            '-',
            '-',
            "This field cannot be sorted against."
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_get_result_row_link(self):
        """Assert that links to the object are added correctly."""
        view = self.get_view(self.get_request(), list_display_links=['name', 'alias'])
        obj = self.get_annotated_model_obj(self.obj)
        expected = [
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Led Zeppelin</a>',
            f'<a href="{self.change_path.format(pk=self.obj.pk)}">Zepp</a>',
            'Jimmy Page, Robert Plant',
            'United Kingdom',
            'This field cannot be sorted against.'
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
            'Led Zeppelin',
            'Zepp',
            'Jimmy Page, Robert Plant',
            'United Kingdom',
            'This field cannot be sorted against.'
        ]
        self.assertEqual(view.get_result_row(obj), expected)

    def test_get_result_row_link_no_change_permission(self):
        """No link should be displayed if the user does not have view permission."""
        request = self.get_request(user=self.noperms_user)
        view = self.get_view(request, list_display_links=["name"])
        obj = self.get_annotated_model_obj(self.obj)
        self.assertNotIn('<a href="', view.get_result_row(obj)[0])

    def test_get_result_row_link_contains_preserved_filters(self):
        """
        The change page links in a row should contain the changelist request
        parameters.
        """
        # NOTE: why? what's the benefit of this?
        request = self.get_request(data={'p': ['1']})
        view = self.get_view(request)
        obj = self.get_annotated_model_obj(self.obj)
        self.assertIn('p=1', view.get_result_row(obj)[0])

    def test_get_query_string_add_params(self):
        request = self.get_request(data={'o': ['1']})
        view = self.get_view(request)
        self.assertEqual(
            view.get_query_string(new_params={'p': '2'}),
            "?o=1&p=2"
        )

    def test_get_query_string_remove_params(self):
        request = self.get_request(data={'o': ['1'], 'p': ['2'], 'q': ["Beep"]})
        view = self.get_view(request)
        self.assertEqual(
            view.get_query_string(new_params={'p': None}, remove=['o']),
            "?q=Beep"
        )

    def test_get_ordering_field(self):
        test_data = [("name", "name"), ("members", "members_list"), ("foo", None)]
        view = self.get_view(self.get_request())
        for name, expected in test_data:
            with self.subTest(name=name):
                self.assertEqual(view.get_ordering_field(name), expected)

    def test_get_queryset_adds_select_related(self):
        """get_queryset should add select_related."""
        queryset = self.get_view(self.get_request()).get_queryset()
        self.assertIn('origin', queryset.query.select_related)

    def test_get_queryset_adds_changelist_annotations(self):
        """get_queryset should add changelist annotations.."""
        queryset = self.get_view(self.get_request()).get_queryset()
        self.assertIn('members_list', queryset.query.annotations)

    def test_get_context_data(self):
        """Assert that get_context_data adds the expected items."""
        view = self.get_view(self.get_request())
        view.object_list = view.get_queryset().order_by('id')
        context = view.get_context_data()
        for context_item in ["page_range", "cl", "result_headers", "result_rows"]:
            with self.subTest(context_item=context_item):
                self.assertIn(context_item, context)
