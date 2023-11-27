from django.test import override_settings
from django.urls import path, include

from dbentry.utils.html import create_hyperlink, get_obj_link, link_list, get_changelist_link
from tests.case import DataTestCase, RequestTestCase
from tests.model_factory import make
from .admin import admin_site
from .models import Audio


def dummy_view(*args, **kwargs):
    pass


class URLConf:
    patterns = [
        path('', dummy_view, name='test_utils_audio_changelist'),
        path('add/', dummy_view, name='test_utils_audio_add'),
        path('<path:object_id>/change/', dummy_view, name='test_utils_audio_change'),
        path('<path:object_id>/delete/', dummy_view, name='test_utils_audio_delete'),
        path('<path:object_id>/history/', dummy_view, name='test_utils_audio_history'),
    ]
    urlpatterns = [
        path('audio/', include(patterns)),
        path('admin/', admin_site.urls)
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestHTMLUtils(DataTestCase, RequestTestCase):
    model = Audio

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = make(cls.model, titel='Testaudio')
        cls.obj2 = make(cls.model, titel='Other Object')
        cls.test_data = [cls.obj1, cls.obj2]
        super().setUpTestData()

    def test_create_hyperlink(self):
        self.assertHTMLEqual(
            create_hyperlink('/foo/bar/', 'Foobar', target="_blank"),
            '<a href="/foo/bar/" target="_blank">Foobar</a>'
        )

    ################################################################################################
    # test get_obj_link
    ################################################################################################

    def test_get_obj_link(self):
        """Assert that the expected link is returned by get_obj_link."""
        for namespace in ('', 'admin'):
            with self.subTest(namespace=namespace):
                prefix = '/admin/test_utils' if namespace else ''
                self.assertHTMLEqual(
                    get_obj_link(self.get_request(), self.obj1, namespace),
                    f'<a href="{prefix}/audio/{self.obj1.pk}/change/">{self.obj1}</a>'
                )

    def test_get_obj_link_blank(self):
        """Assert that the returned link has target="_blank"."""
        self.assertIn(
            'target="_blank"',
            get_obj_link(self.get_request(), self.obj1, blank=True)
        )

    def test_get_obj_link_no_change_permission(self):
        """
        No link should be displayed if the user does not have change
        permissions.
        """
        self.assertEqual(get_obj_link(self.get_request(user=self.noperms_user), self.obj1), str(self.obj1))

    def test_get_obj_link_no_reverse_match(self):
        """No link should be displayed if there is no reverse match."""

        class URLConf:
            urlpatterns = []

        with override_settings(ROOT_URLCONF=URLConf):
            link = get_obj_link(self.get_request(), self.obj1)
        self.assertEqual(link, str(self.obj1))

    ################################################################################################
    # test link_list
    ################################################################################################

    def test_link_list(self):
        """Assert that the expected links are returned by link_list."""
        for namespace in ('', 'admin'):
            with self.subTest(namespace=namespace):
                prefix = '/admin/test_utils' if namespace else ''
                links = link_list(
                    self.get_request(user=self.super_user),
                    obj_list=[self.obj1, self.obj2],
                    namespace=namespace,
                    sep="$"
                )
                for i, link in enumerate(links.split("$")):
                    with self.subTest(link=link):
                        obj = self.test_data[i]
                        self.assertHTMLEqual(
                            link,
                            f'<a href="{prefix}/audio/{obj.pk}/change/">{obj}</a>'
                        )

    def test_link_list_blank(self):
        """
        Assert that all links returned by link_list have the target attribute
        set to "_blank".
        """
        links = link_list(
            self.get_request(user=self.super_user),
            obj_list=[self.obj1, self.obj2],
            sep="$",
            blank=True
        )
        for link in links.split("$"):
            with self.subTest(link=link):
                self.assertIn('target="_blank"', link)

    ################################################################################################
    # test get_changelist_link
    ################################################################################################

    def test_get_changelist_link(self):
        """Assert that the expected link is returned by get_changelist_link."""
        for namespace in ('', 'admin'):
            with self.subTest(namespace=namespace):
                prefix = '/admin/test_utils' if namespace else ''
                self.assertHTMLEqual(
                    get_changelist_link(self.get_request(), self.model, namespace=namespace),
                    f'<a href="{prefix}/audio/">Liste</a>'
                )

    def test_get_changelist_link_blank(self):
        """
        Assert that the expected link, with target="_blank", is returned by
        get_changelist_link.
        """
        self.assertIn(
            'target="_blank"',
            get_changelist_link(self.get_request(), self.model, blank=True),
        )
