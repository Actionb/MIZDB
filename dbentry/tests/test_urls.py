from django.urls import resolve, reverse
from django.urls.exceptions import NoReverseMatch, Resolver404

from MIZDB import urls as mizdb_urls
from dbentry import urls as dbentry_urls
from dbentry.ac import urls as autocomplete_urls, views as autocomplete_views
from dbentry.ac.widgets import GENERIC_URL_NAME
from dbentry.bulk import views as bulk_views
from dbentry.maint import urls as maint_urls, views as maint_views
from dbentry.sites import miz_site
from dbentry.tests.base import MyTestCase


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
                view_name, args=args, kwargs=kwargs, urlconf=urlconf, current_app=current_app
            )
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
            ('bulk_ausgabe', '/tools/bulk_ausgabe', bulk_views.BulkAusgabe),
        ]
        for view_name, url, view_class in expected:
            with self.subTest(view_name=view_name, url=url):
                self.assertReverses(view_name, url)
                self.assertResolves(url, view_class)

    def test_autocomplete_urls(self):
        """Test the explicit autocomplete urls."""
        self.urlconf = autocomplete_urls
        test_data = [
            # view name     url    reverse kwargs       view class
            ('acautor', '/autor/', {}, autocomplete_views.ACAutor),
            ('acausgabe', '/ausgabe/', {}, autocomplete_views.ACAusgabe),
            ('acband', '/band/', {}, autocomplete_views.ACBand),
            ('acband', '/band/band_name/', {'create_field': 'band_name'}, autocomplete_views.ACBand),  # noqa
            ('acbuchband', '/buch/', {}, autocomplete_views.ACBuchband),
            ('acmagazin', '/magazin/', {}, autocomplete_views.ACMagazin),
            ('acmagazin', '/magazin/magazin_name/', {'create_field': 'magazin_name'}, autocomplete_views.ACMagazin),  # noqa
            ('acmusiker', '/musiker/', {}, autocomplete_views.ACMusiker),
            ('acmusiker', '/musiker/kuenstler_name/', {'create_field': 'kuenstler_name'}, autocomplete_views.ACMusiker),  # noqa
            ('acperson', '/person/', {}, autocomplete_views.ACPerson),
            ('acspielort', '/spielort/', {}, autocomplete_views.ACSpielort),
            ('acveranstaltung', '/veranstaltung/', {}, autocomplete_views.ACVeranstaltung),
            ('gnd', '/gnd/', {}, autocomplete_views.GND),
            ('autocomplete_user', '/auth_user/', {}, autocomplete_views.UserAutocompleteView),
            ('autocomplete_ct', '/content_type/', {}, autocomplete_views.ContentTypeAutocompleteView),  # noqa
        ]
        for view_name, url, kwargs, view_class in test_data:
            with self.subTest(view_name=view_name, url=url):
                self.assertReverses(view_name, url, **kwargs)
                self.assertResolves(url, view_class)

    def test_autocomplete_urls_generic_view_name(self):
        """
        Assert that the explicit URLs can also be reached via the generic view
        name.
        """
        self.urlconf = autocomplete_urls
        test_data = [
            #  url    reverse kwargs       view class
            ('/autor/', {'model_name': 'autor'}, autocomplete_views.ACAutor),
            ('/ausgabe/', {'model_name': 'ausgabe'}, autocomplete_views.ACAusgabe),
            ('/band/', {'model_name': 'band'}, autocomplete_views.ACBand),
            ('/buch/', {'model_name': 'buch'}, autocomplete_views.ACBuchband),
            ('/magazin/', {'model_name': 'magazin'}, autocomplete_views.ACMagazin),
            ('/musiker/', {'model_name': 'musiker'}, autocomplete_views.ACMusiker),
            ('/person/', {'model_name': 'person'}, autocomplete_views.ACPerson),
            ('/spielort/', {'model_name': 'spielort'}, autocomplete_views.ACSpielort),
            ('/veranstaltung/', {'model_name': 'veranstaltung'}, autocomplete_views.ACVeranstaltung),  # noqa
            (
                '/band/band_name/',
                {'model_name': 'band', 'create_field': 'band_name'},
                autocomplete_views.ACBand
            ),
            (
                '/magazin/magazin_name/',
                {'model_name': 'magazin', 'create_field': 'magazin_name'},
                autocomplete_views.ACMagazin
            ),
            (
                '/musiker/kuenstler_name/',
                {'model_name': 'musiker', 'create_field': 'kuenstler_name'},
                autocomplete_views.ACMusiker
            ),
        ]
        for url, kwargs, view_class in test_data:
            with self.subTest(view_name=GENERIC_URL_NAME, url=url):
                self.assertReverses(GENERIC_URL_NAME, url, **kwargs)
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
