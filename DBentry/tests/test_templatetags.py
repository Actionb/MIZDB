import re

from DBentry import models as _models
from DBentry.templatetags.object_tools import favorites_link
from DBentry.tests.base import RequestTestCase


class TestObjectToolsTags(RequestTestCase):

    def test_favorite_links(self):
        # No popup
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': _models.artikel._meta, 'is_popup': False}))
        self.assertIn(expected, links)

        # As popup
        expected = '<li><a href="/admin/tools/favoriten/?_popup=1" onclick="return popup(this)">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': _models.artikel._meta, 'is_popup': True}))
        self.assertIn(expected, links)
