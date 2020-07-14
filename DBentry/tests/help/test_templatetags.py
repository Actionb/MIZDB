from .base import HelpRegistryMixin, add_urls
from ..base import RequestTestCase

from unittest.mock import patch

from django import views
from django.conf.urls import url, include

from DBentry.models import artikel
from DBentry.help.helptext import ModelAdminHelpText, FormViewHelpText
from DBentry.help.templatetags import help_link

class TestHelpLinks(HelpRegistryMixin, RequestTestCase):
    
    def test_help_links_model_admin(self):
        with patch('DBentry.help.registry.halp', new = self.registry):
            artikel_help = type('ArtikelHelpText', (ModelAdminHelpText, ), {'model':artikel})
            self.registry.register(artikel_help, url_name = None)
        
            with self.add_urls():
                # No popup
                request = self.get_request('/admin/DBentry/artikel/add', follow = True)
                expected = '<li><a href="/admin/help/artikel/" target="_blank">Hilfe</a></li>'
                self.assertEqual(help_link({'request': request, 'is_popup': False}), expected)

                # As popup
                expected = '<li><a href="/admin/help/artikel/?_popup=1" onclick="return popup(this)">Hilfe</a></li>'
                self.assertEqual(help_link({'request': request, 'is_popup': True}), expected)
                
                # No help page for that model
                request = self.get_request('/admin/DBentry/spielort/add', follow = True)
                self.assertEqual(help_link({'request': request, 'is_popup': False}), '')
        
    def test_help_links_form(self):
        # Create a dummy target view and an url to it for the HelpText 
        target_view_class = type('DummyView', (views.View, ), {'form_class':None})
        target_view_pattern = url(r'^dummy_view/', target_view_class.as_view(), name = 'dummy_view')
        
        # help_link imports halp, so we need to patch it with this test's registry
        with patch('DBentry.help.registry.halp', new = self.registry):
        
            with add_urls(url_patterns = [target_view_pattern, url(r'^help/', include(self.registry.get_urls()))], regex = r'^test/'):
                request = self.get_request('/test/dummy_view/')
                # No help page for that form
                self.assertEqual(help_link({'request': request, 'is_popup': False}), '')   
            
            # Create the actualy FormViewHelpText class and register it
            # the url path to it is its url_name without the 'help_' bit
            form_help = type('SomeFormHelp', (FormViewHelpText, ), {'target_view_class':target_view_class})
            self.registry.register(form_help, url_name = 'help_dummy_view')
            
            with add_urls(url_patterns = [target_view_pattern, url(r'^help/', include(self.registry.get_urls()))] , regex = r'^test/'):
                request = self.get_request('/test/dummy_view/')
                # No popup
                expected = '<li><a href="/test/help/dummy_view/" target="_blank">Hilfe</a></li>'
                self.assertEqual(help_link({'request': request, 'is_popup': False}), expected)
                
                # As popup
                expected = '<li><a href="/test/help/dummy_view/?_popup=1" onclick="return popup(this)">Hilfe</a></li>'
                self.assertEqual(help_link({'request': request, 'is_popup': True}), expected)
             
    
