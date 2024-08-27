from django.test import override_settings
from django.urls import include, path

from dbentry.utils import url
from tests.case import DataTestCase, RequestTestCase

from ..model_factory import make
from .models import Musiker


def dummy_view(*args, **kwargs):
    pass


class URLConf:
    patterns = [
        path('changelist/', dummy_view, name='test_utils_musiker_changelist'),
        path('add/', dummy_view, name='test_utils_musiker_add'),
        path('<path:object_id>/change/', dummy_view, name='test_utils_musiker_change'),
        path('<path:object_id>/delete/', dummy_view, name='test_utils_musiker_delete'),
        path('<path:object_id>/history/', dummy_view, name='test_utils_musiker_history'),
    ]
    urlpatterns = [
        path('musiker/', include(patterns))
    ]


@override_settings(ROOT_URLCONF=URLConf)
class TestURLs(DataTestCase, RequestTestCase):
    model = Musiker

    @classmethod
    def setUpTestData(cls):
        cls.obj = make(Musiker)
        super().setUpTestData()

    def test_urlname(self):
        opts = self.model._meta
        test_data = [
            # args                  expected
            (('index',), 'index'),
            (('add', opts), 'test_utils_musiker_add'),
            (('change', opts, 'foobar'), 'foobar:test_utils_musiker_change')
        ]
        for args, expected in test_data:
            with self.subTest(args=args):
                self.assertEqual(url.urlname(*args), expected)

    @override_settings(ANONYMOUS_CAN_VIEW=False)
    def test_get_changelist_url(self):
        request = self.get_request()
        self.assertEqual(
            url.get_changelist_url(request, Musiker),
            '/musiker/changelist/'
        )
        self.assertEqual(
            url.get_changelist_url(request, Musiker, [self.obj]),
            f'/musiker/changelist/?id__in={self.obj.pk}'
        )

        request.user = self.noperms_user
        self.assertFalse(url.get_changelist_url(request, Musiker))

    def test_get_add_url(self):
        request = self.get_request()
        self.assertEqual(
            url.get_add_url(request, Musiker),
            '/musiker/add/'
        )

        request.user = self.noperms_user
        self.assertFalse(url.get_add_url(request, Musiker))

    def test_get_change_url(self):
        request = self.get_request()
        self.assertEqual(
            url.get_change_url(request, self.obj),
            f'/musiker/{self.obj.pk}/change/'
        )

        request.user = self.noperms_user
        self.assertFalse(url.get_change_url(request, self.obj))

    def test_get_delete_url(self):
        request = self.get_request()
        self.assertEqual(
            url.get_delete_url(request, self.obj),
            f'/musiker/{self.obj.pk}/delete/'
        )

        request.user = self.noperms_user
        self.assertFalse(url.get_delete_url(request, self.obj))

    @override_settings(ANONYMOUS_CAN_VIEW=False)
    def test_get_history_url(self):
        request = self.get_request()
        self.assertEqual(
            url.get_history_url(request, self.obj),
            f'/musiker/{self.obj.pk}/history/'
        )

        request.user = self.noperms_user
        self.assertFalse(url.get_history_url(request, self.obj))
