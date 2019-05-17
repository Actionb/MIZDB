from django.urls import reverse, resolve
from django.urls.exceptions import NoReverseMatch, Resolver404

from .base import MyTestCase

from DBentry.sites import miz_site
from DBentry.bulk import views as bulk_views

from MIZDB import urls as mizdb_urls
from DBentry import urls as dbentry_urls, views as dbentry_views
from DBentry.ac import urls as autocomplete_urls, views as autocomplete_views
#from DBentry.help import urls as help_urls, views as help_views
from DBentry.maint import urls as maint_urls, views as maint_views

class URLTestCase(MyTestCase):
    
    urlconf = None
    current_app = None
    
    def assertReverses(self, view_name, expected  = None, *args, **kwargs):
        if 'urlconf' in kwargs:
            urlconf = kwargs.pop('urlconf')
        else:
            urlconf = self.urlconf
        if 'current_app' in kwargs:
            current_app = kwargs.pop('current_app')
        else:
            current_app = self.current_app
        
        try:
            reversed = reverse(view_name, args = args, kwargs = kwargs, urlconf = urlconf, current_app = current_app)
        except NoReverseMatch as e:
            raise AssertionError(e.args[0])
        if expected is not None:
            self.assertEqual(reversed, expected)
        
    def assertResolves(self, url, expected = None, **kwargs):
        if 'urlconf' in kwargs:
            urlconf = kwargs.pop('urlconf')
        else:
            urlconf = self.urlconf
            
        try:
            resolved = resolve(url, urlconf = urlconf)
        except Resolver404 as e:
            raise AssertionError(e.args[0])
        if expected is not None:
            if hasattr(resolved.func, 'view_class'):
                self.assertEqual(resolved.func.view_class, expected)
            else:
                self.assertEqual(resolved.func.__wrapped__.__func__, expected)
            
class TestURLs(URLTestCase):
    
    def test_mizdb_urls(self):
        # Tests the root urls in MIZDB.urls.py
        self.urlconf = mizdb_urls
        self.assertReverses('admin:index', '/admin/')
        self.assertResolves('/admin/', miz_site.index.__func__) # miz_site.index is a bound function
        
        self.assertReverses('admin:app_list', app_label = 'DBentry')
        self.assertResolves('/admin/DBentry/', miz_site.app_index.__func__)
        
    def test_dbentry_urls(self):
        # Tests the urls in DBentry.urls.py
        self.urlconf = dbentry_urls
        
        expected = [
            ('bulk_ausgabe', '/tools/bulk_ausgabe/', bulk_views.BulkAusgabe), 
            ('favoriten', '/tools/favoriten/', dbentry_views.FavoritenView)
        ]
        with self.collect_fails() as collector:
            for view_name, url, view_class in expected:
                with collector():
                    self.assertReverses(view_name, url)
                    self.assertResolves(url, view_class)
        
    def test_autocomplete_urls(self):
        # Tests the urls in DBentry.ac.urls.py
        self.urlconf = autocomplete_urls
        
        expected = [
            ('acbuchband', '/buch/', (), {}, autocomplete_views.ACBuchband), 
            ('acausgabe', '/ausgabe/', (), {}, autocomplete_views.ACAusgabe), 
            ('accapture', '/musiker/kuenstler_name/', (), 
                {'model_name': 'musiker', 'create_field': 'kuenstler_name'}, autocomplete_views.ACBase), 
            ('accapture', '/autor/', (), {'model_name': 'autor'}, autocomplete_views.ACCreateable)
        ]
        with self.collect_fails() as collector:
            for view_name, url, args, kwargs, view_class in expected:
                with collector():
                    self.assertReverses(view_name, url, *args, **kwargs)
                    self.assertResolves(url, view_class)
        
    def test_help_urls(self):
        pass
        
    def test_maint_urls(self):
        self.urlconf = maint_urls
        
        expected = [
            ('dupes_select', '/dupes/', (), {}, maint_views.ModelSelectView), 
            ('dupes', '/dupes/ausgabe/', (), {'model_name':'ausgabe'}, maint_views.DuplicateObjectsView), 
#            ('unused_select', '/unused/', (), {}, maint_views.ModelSelectView), 
#            ('unused_objects', '/unused/ausgabe/lte1/', (), {'model_name': 'ausgabe', 'lte': 1}, maint_views.UnusedObjectsView)
        ]
        with self.collect_fails() as collector:
            for view_name, url, args, kwargs, view_class in expected:
                with collector():
                    self.assertReverses(view_name, url, *args, **kwargs)
                    self.assertResolves(url, view_class)
                    
    def test_miz_site_urls(self):
        pass
