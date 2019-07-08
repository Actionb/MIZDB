import re

from .base import RequestTestCase

from DBentry import models as _models
from DBentry.templatetags.object_tools import favorites_link

class TestObjectToolsTags(RequestTestCase):
        
    def test_favorite_links(self):
        # No popup
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': _models.artikel._meta, 'is_popup': False}))
        self.assertIn(expected, links)
        
        # No favoriten for that model
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': _models.sender._meta, 'is_popup': False}))
        self.assertNotIn(expected, links)
        
        # As popup
        expected = '<li><a href="/admin/tools/favoriten/?_popup=1" onclick="return popup(this)">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': _models.artikel._meta, 'is_popup': True}))
        self.assertIn(expected, links)
        
