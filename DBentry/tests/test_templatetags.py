import re

from .base import RequestTestCase, AdminTestCase

from DBentry.models import artikel, sender, ausgabe, magazin
from DBentry.admin import AusgabenAdmin, MagazinAdmin, miz_site
from DBentry.advsfforms import advSF_factory
from DBentry.templatetags.object_tools import favorites_link
from DBentry.templatetags.asf_tag import advanced_search_form

class TestObjectToolsTags(RequestTestCase):
        
    def test_favorite_links(self):
        # No popup
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': artikel._meta, 'is_popup': False}))
        self.assertIn(expected, links)
        
        # No favoriten for that model
        expected = '<li><a href="/admin/tools/favoriten/" target="_blank">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': sender._meta, 'is_popup': False}))
        self.assertNotIn(expected, links)
        
        # As popup
        expected = '<li><a href="/admin/tools/favoriten/?_popup=1" onclick="return popup(this)">Favoriten</a></li>'
        links = re.findall('<li>.+?</li>', favorites_link({'opts': artikel._meta, 'is_popup': True}))
        self.assertIn(expected, links)
        
    
class TestAdvSearchFormTags(AdminTestCase):
    
    model = ausgabe
    model_admin_class = AusgabenAdmin
    
    def setUp(self):
        super().setUp()
        self.asf_dict = advanced_search_form(self.get_changelist(self.get_request()))['asf']
    
    def test_ignores_fields_already_in_formfields(self):
        # Assert that fields that are in advanced_search_form['selects'] and already in the search form (which only contains the dal stuff)
        # as formfields are not added yet again to the asf['selects'] category.
        form_class = advSF_factory(self.model_admin)
        
        # We only want the query_string's of the selects:
        selects = [d['query_string'] for d in self.asf_dict['selects']]
        
        #TODO: add collect_fails() when it has been merged into master
        # Any field declared on the form should not show up a second time in the selects
        for field_name in form_class.base_fields:
            self.assertNotIn(field_name, selects)
            
        # Any field declared in the selects should not show up in the form
        for field_name in selects:
            self.assertNotIn(field_name, form_class.base_fields)
        
    def test_asf_select_contents(self):
        # Assert that asf['select'] contains the right parameters for the template
        
        # selects is a list of dicts with these key, value pairs: 
        # (label, the label)
        # (query_string, the field.attname; enabling directly querying with the name of the widget)
        # (choices, the choices)
        
        selects = self.asf_dict['selects']
        
        # The advanced_search_form for AusgabenAdmin only contains one simple select: status
        self.assertEqual(len(selects), 1)
        selects = selects.pop() # get the underlying dict directly
        status_field = ausgabe._meta.get_field('status')
        self.assertIn('status', status_field.attname)
        self.assertEqual(selects['query_string'], status_field.attname) # bit redundant, yes
        self.assertEqual(selects['label'], status_field.verbose_name) # labels are not that important, but in this case we know exactly what it should be
        # Choices are a dict with keys pk, displayed_str, selected (boolean)
        status_field_choices = status_field.get_choices()
        self.assertEqual(len(selects['choices']), len(status_field_choices))
        for pk, displayed_str in ((d['pk'], d['display']) for d in selects['choices']):
            self.assertIn((pk, displayed_str), status_field_choices)
            

    def test_asf_gtelt_contents_no_initial(self):
        # Assert that asf['gtelt'] contains the right parameters for the template.
        
        # gtelts has the following structure:
        # (label, the label)
        # (gte_query_string, the name of the widget for the gte part)
        # (gte_val, the value of that widget)
        # (lt_query_string, same as query_string for gte)
        # (lt_val, same as value of gte_val)
        
        gtelts = self.asf_dict['gtelt']
        
        for gtelt in gtelts:
            field_name = gtelt['gte_query_string'].replace('__gte', '')
            self.assertIn(field_name, self.model_admin.advanced_search_form['gtelt'])
            self.assertEqual(gtelt['gte_val'], '')
            field_name = gtelt['lt_query_string'].replace('__lt', '')
            self.assertIn(field_name, self.model_admin.advanced_search_form['gtelt'])
            self.assertEqual(gtelt['lt_val'], '')
        
    def test_asf_gtelt_contents_with_initial(self):
        # Assert that the gtelt elements get their right initital values from request.GET
        request = self.get_request(
            data = {'ausgabe_jahr__jahr':'1981', 'ausgabe_num__num__gte' : '1', 'ausgabe_num__num__lt' : '3'}
        )
        gtelts = advanced_search_form(self.get_changelist(request))['asf']['gtelt']
        
        for gtelt in gtelts:
            field_name = gtelt['gte_query_string'].replace('__gte', '')
            if field_name == 'ausgabe_jahr__jahr':
                self.assertEqual(gtelt['gte_val'], '1981')
                self.assertEqual(gtelt['lt_val'], '')
            elif field_name == 'ausgabe_num__num':
                self.assertEqual(gtelt['gte_val'], '1')
                self.assertEqual(gtelt['lt_val'], '3')
            else:
                self.assertEqual(gtelt['gte_val'], '')
                self.assertEqual(gtelt['lt_val'], '')
        
    def test_asf_simple_contents(self):
        # Assert that asf['simple'] contains the right parameters for the template
        # 1. no boolean
        # 2. boolean
        
        # simples has the following structure:
        # (label, the label)
        # (query_string, field_name/name of widget)
        # (val, the initial value)
        # (bool, boolean value if this is a BooleanField)
        #NOTE: blergh, this test is not so great
        self.model_admin = MagazinAdmin(magazin, miz_site)
        simples = advanced_search_form(self.get_changelist(self.get_request()))['asf']['simple']
        
        for simple in simples:
            if simple['query_string'] == 'issn':
                self.assertFalse(simple['bool'])
            elif simple['query_string'] == 'fanzine':
                self.assertTrue(simple['bool'])
            else:
                self.fail("Unknown simple search field for MagazinAdmin.advanced_search_form: " + simple['query_string'])
        
    
