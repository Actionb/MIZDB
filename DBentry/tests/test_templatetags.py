from .base import *

from DBentry.templatetags.object_tools import object_tools

@tag("wip")
class TestObjectTools(TestCase):
    
    def test_help_links(self):
        # No popup
        expected = '<li><a href="/admin/help/artikel/" target="_blank">Hilfe</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(artikel._meta, is_popup = False))
        self.assertIn(expected, links)
        
        # No help page for that model
        expected = '<li><a href="/admin/help/sender/" target="_blank">Hilfe</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(sender._meta, is_popup = False))
        self.assertNotIn(expected, links)
        
    def test_help_links_popup(self):
        # As popup
        expected = '<li><a href="/admin/help/artikel/?_popup=1" onclick="return popup(this)">Hilfe</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(artikel._meta, is_popup = True))
        self.assertIn(expected, links)
        
        
    def test_favorite_links(self):
        # No popup
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(artikel._meta, is_popup = False))
        self.assertIn(expected, links)
        
        # No favoriten for that model
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(sender._meta, is_popup = False))
        self.assertNotIn(expected, links)
        
    def test_favorite_links_popup(self):
        # As popup
        expected = '<li><a href="/admin/tools/favoriten/?_popup=1" onclick="return popup(this)">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', object_tools(artikel._meta, is_popup = True))
        self.assertIn(expected, links)
        
    
class TestAdvSearchForm(TestCase):
    pass
