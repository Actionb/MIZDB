from ..base import MyTestCase

from DBentry import models as _models
from DBentry.ac import widgets as autocomplete_widgets
from DBentry.factory import make
from DBentry.search import forms as search_forms

class TestSearchFormFactory(MyTestCase):
    
    factory = search_forms.SearchFormFactory()
    
    def test_formfield_for_dbfield_dal(self):
        # Assert that formfield_for_dbfield prepares an autocomplete ready formfield.
        dbfield = _models.ausgabe._meta.get_field('magazin')
        formfield = self.factory.formfield_for_dbfield(dbfield)
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2)
        self.assertEqual(widget.model_name, _models.magazin._meta.model_name)
        msg = "Should not be allowed to create new records from inside a search form."
        self.assertFalse(widget.create_field, msg = msg)
        self.assertEqual(formfield.queryset.model, _models.magazin)
        self.assertFalse(formfield.required)
        
        dbfield = _models.artikel._meta.get_field('genre')
        formfield = self.factory.formfield_for_dbfield(dbfield)
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2Multiple)
        self.assertEqual(widget.model_name, _models.genre._meta.model_name)
        msg = "Should not be allowed to create new records from inside a search form."
        self.assertFalse(widget.create_field, msg = msg)
        self.assertEqual(formfield.queryset.model, _models.genre)
        self.assertFalse(formfield.required)
        
        # Test with a forward
        dbfield = _models.ausgabe._meta.get_field('magazin')
        formfield = self.factory.formfield_for_dbfield(dbfield, forward = ['ausgabe'])
        widget = formfield.widget
        self.assertIsInstance(widget, autocomplete_widgets.MIZModelSelect2)
        self.assertTrue(widget.forward)
        
    def test_get_search_form(self):
        fields = ['seite__gt', 'seitenumfang', 'genre__genre', 'notafield', 'schlagwort__notalookup']
        form_class = self.factory(_models.artikel, fields)
        self.assertIn('seite__gt', form_class.base_fields)
        self.assertIn('seitenumfang', form_class.base_fields)
        self.assertIn('genre__genre', form_class.base_fields)
        self.assertNotIn('notafield', form_class.base_fields)
        self.assertNotIn('schlagwort__notalookup', form_class.base_fields)
        self.assertEqual(form_class.range_start_suffix, '__gte')
        self.assertEqual(form_class.range_end_suffix, '__lt')
    
class TestSearchForm(MyTestCase):
    
    model = _models.artikel
    
    def test_get_filters_params_skips_empty(self):
        # Assert that get_filter_params does not return empty query values.
        data = {
            'seite': 1, 
            'ausgabe__magazin': make(_models.magazin).pk, 
            'musiker': []
        }
        form_class =  search_forms.SearchFormFactory()(self.model, fields = data.keys())
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertIn('seite', filter_params)
        self.assertIn('ausgabe__magazin', filter_params)
        self.assertNotIn('musiker', filter_params)
        
    def test_get_filters_params_replaces_range_with_exact(self):
        # Assert that get_filter_params replaces a range query with no end 
        # with a query for exact.
        data = {'seite__gte': 1, 'seite__lt': None}
        form_class =  search_forms.SearchFormFactory()(self.model, fields = data.keys())
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertNotIn('seite__lt', filter_params)
        self.assertNotIn('seite__gte', filter_params)
        self.assertIn('seite', filter_params)
