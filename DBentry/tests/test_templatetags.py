from .base import *

from django.views import View
from django.conf.urls import url
from django.test.utils import override_settings

from DBentry.templatetags.object_tools import help_link, favorites_link
from DBentry.help.registry import halp

DummyForm = type('DummyForm', (forms.Form, ), {})
    
# The view the request will resolve to
DummyFormView  = type('DummyFormView', (View, ), {'form_class':DummyForm})

# The view to the url_name registered in halp._registry['forms']
DummyHelpTextView  = type('DummyHelpTextView', (View, ), {'form_class':DummyForm})
    
DummyFormHelpText = type('DummyFormHelpText', (object, ), {'form_class':DummyForm})

urlpatterns = [
    url(r'^test/', DummyFormView.as_view(), name = 'test_url'), 
    url(r'^help/test/', DummyHelpTextView.as_view(), name = 'test_helptext')
]

class TestHelpLinks(RequestTestCase):
    
    fake_help_registry = {
        'models': {artikel:'Beep boop'}, 
        'forms': {'test_helptext': DummyFormHelpText}
    }
    
    @patch.dict(halp._registry, fake_help_registry)
    def test_help_links_model_admin(self):
        # No popup
        request = self.get_request('/admin/DBentry/artikel/add', follow = True)
        expected = '<li><a href="/admin/help/artikel/" target="_blank">Hilfe</a></li>'
        self.assertEqual(help_link(request, is_popup = False), expected)

        # As popup
        expected = '<li><a href="/admin/help/artikel/?_popup=1" onclick="return popup(this)">Hilfe</a></li>'
        self.assertEqual(help_link(request, is_popup = True), expected)
        
        # No help page for that model
        request = self.get_request('/admin/DBentry/sender/add', follow = True)
        self.assertEqual(help_link(request, is_popup = False), '')
    
    @patch.dict(halp._registry, fake_help_registry)
    @override_settings(ROOT_URLCONF=__name__)
    def test_help_links_form(self):
        # No popup
        request = self.get_request('/test/')
        expected = '<li><a href="/help/test/" target="_blank">Hilfe</a></li>'
        self.assertEqual(help_link(request, is_popup = False), expected)
        
        # As popup
        expected = '<li><a href="/help/test/?_popup=1" onclick="return popup(this)">Hilfe</a></li>'
        self.assertEqual(help_link(request, is_popup = True), expected)
        
        # HelpText object and the view do not have the same form class
        halp._registry['forms']['test_helptext'].form_class = 'This is not a form!'
        self.assertEqual(help_link(request, is_popup = False), '')
        
        # No help page for that form
        del halp._registry['forms']['test_helptext']
        self.assertEqual(help_link(request, is_popup = False), '')        
    

class TestObjectTools(RequestTestCase):
        
    def test_favorite_links(self):
        # No popup
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link(artikel._meta, is_popup = False))
        self.assertIn(expected, links)
        
        # No favoriten for that model
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link(sender._meta, is_popup = False))
        self.assertNotIn(expected, links)
        
        # As popup
        expected = '<li><a href="/admin/tools/favoriten/?_popup=1" onclick="return popup(this)">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link(artikel._meta, is_popup = True))
        self.assertIn(expected, links)
        
    
class TestAdvSearchForm(TestCase):
    pass
