from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch, Resolver404

from dbentry import urls as dbentry_urls
from dbentry.ac import urls as autocomplete_urls, views as autocomplete_views
from dbentry.bulk import views as bulk_views
from dbentry.maint import urls as maint_urls, views as maint_views
from dbentry.sites import miz_site
from dbentry.tests.base import MyTestCase

from MIZDB import urls as mizdb_urls


class URLTestCase(MyTestCase):

    urlconf = None
    current_app = None

    def assertReverses(self, view_name, expected=None, *args, **kwargs):
        if 'urlconf' in kwargs:
            urlconf = kwargs.pop('urlconf')
        else:
            urlconf = self.urlconf
        if 'current_app' in kwargs:
            current_app = kwargs.pop('current_app')
        else:
            current_app = self.current_app

        try:
            _reversed = reverse(
                view_name, args=args, kwargs=kwargs, urlconf=urlconf, current_app=current_app)
        except NoReverseMatch as e:
            raise AssertionError(e.args[0])
        if expected is not None:
            self.assertEqual(_reversed, expected)

    def assertResolves(self, url, expected=None, **kwargs):
        if 'urlconf' in kwargs:
            urlconf = kwargs.pop('urlconf')
        else:
            urlconf = self.urlconf

        try:
            resolved = resolve(url, urlconf=urlconf)
        except Resolver404 as e:
            raise AssertionError(e.args[0])
        if expected is not None:
            if hasattr(resolved.func, 'view_class'):
                self.assertEqual(resolved.func.view_class, expected)
            else:
                self.assertEqual(resolved.func.__wrapped__.__func__, expected)


class TestURLs(URLTestCase):

    def test_mizdb_urls(self):
        # Tests the root urls in MIZDB.urls.py.
        self.urlconf = mizdb_urls
        self.assertReverses('admin:index', '/admin/')
        # miz_site.index is a bound function:
        self.assertResolves('/admin/', miz_site.index.__func__)

        self.assertReverses('admin:app_list', app_label='dbentry')
        self.assertResolves('/admin/dbentry/', miz_site.app_index.__func__)

    def test_dbentry_urls(self):
        # Tests the urls in dbentry.urls.py.
        self.urlconf = dbentry_urls

        expected = [
            ('bulk_ausgabe', '/tools/bulk_ausgabe/', bulk_views.BulkAusgabe),
        ]
        for view_name, url, view_class in expected:
            with self.subTest(view_name=view_name, url=url):
                self.assertReverses(view_name, url)
                self.assertResolves(url, view_class)

    def test_autocomplete_urls(self):
        # Tests the urls in dbentry.ac.urls.py.
        self.urlconf = autocomplete_urls
        expected = [
            ('acbuchband', '/buch/', (), {}, autocomplete_views.ACBuchband),
            ('acausgabe', '/ausgabe/', (), {}, autocomplete_views.ACAusgabe),
            (
                'accapture', '/musiker/kuenstler_name/', (),
                {'model_name': 'musiker', 'create_field': 'kuenstler_name'},
                autocomplete_views.ACBase
            ),
            (
                'accapture', '/autor/', (),
                {'model_name': 'autor'},
                autocomplete_views.ACCreatable
            )
        ]
        for view_name, url, args, kwargs, view_class in expected:
            with self.subTest(view_name=view_name, url=url):
                self.assertReverses(view_name, url, *args, **kwargs)
                self.assertResolves(url, view_class)

    def test_maint_urls(self):
        self.urlconf = maint_urls
        test_data = [
            (
                'dupes_select', '/dupes/', (), {},
                maint_views.DuplicateModelSelectView
            ),
            (
                'dupes', '/dupes/ausgabe/', (), {'model_name': 'ausgabe'},
                maint_views.DuplicateObjectsView
            )
        ]
        for view_name, url, args, kwargs, view_class in test_data:
            with self.subTest(view_name=view_name):
                self.assertReverses(view_name, url, *args, **kwargs)
                self.assertResolves(url, view_class)
