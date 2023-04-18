from django.test import override_settings
from django.urls import path, include

from dbentry.utils.html import create_hyperlink, get_obj_link
from tests.case import DataTestCase, RequestTestCase
from tests.model_factory import make
from .admin import admin_site
from .models import Audio


def dummy_view(*args, **kwargs):
    pass


class URLConf:
    patterns = [
        path('changelist/', dummy_view, name='test_utils_audio_changelist'),
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
        url = f'/audio/{self.obj1.pk}/change/'
        for namespace in ('', 'admin'):
            with self.subTest(namespace=namespace):
                if namespace:
                    url = '/admin/test_utils' + url
                self.assertEqual(
                    get_obj_link(self.get_request(), self.obj1, namespace),
                    f'<a href="{url}">{self.obj1}</a>'
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
        self.assertEqual(
            get_obj_link(self.get_request(user=self.noperms_user), self.obj1),
            f"{self.model._meta.verbose_name}: {self.obj1}"
        )

    def test_get_obj_link_no_reverse_match(self):
        """No link should be displayed if there is no reverse match."""

        class URLConf:
            urlpatterns = []

        with override_settings(ROOT_URLCONF=URLConf):
            link = get_obj_link(self.get_request(), self.obj1)
        self.assertEqual(link, f"{self.model._meta.verbose_name}: {self.obj1}")
