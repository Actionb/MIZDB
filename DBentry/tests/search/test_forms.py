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
        
    def test_takes_formfield_callback(self):
        # Assert that custom formfield_callback can be passed to the factory 
        # and that it uses that to create formfields for dbfields.
        callback = lambda dbfield: 'This is not a field!'
        form_class = self.factory(_models.artikel, formfield_callback = callback, fields = ['seite'])
        self.assertEqual(getattr(form_class, 'seite', None), 'This is not a field!')
        # A callback that is not a callable should raise a TypeError
        with self.assertRaises(TypeError):
            self.factory(_models.artikel, formfield_callback = 1)
        
        
    
class TestSearchForm(MyTestCase):
    
    model = _models.artikel
    
    def test_get_filters_params_returns_empty_on_invalid(self):
        form_class = search_forms.SearchFormFactory()(self.model)
        form = form_class()
        # Empty form without data => is_valid == False
        self.assertFalse(form.get_filter_params())
    
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
        
    def test_get_filters_params_range(self):
        form_class =  search_forms.SearchFormFactory()(self.model, fields = ['seite__range'])
        data = {'seite__range_0': '1', 'seite__range_1': '2'}
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertIn('seite__range', filter_params)
        self.assertEqual(filter_params['seite__range'], [1, 2])
        # Little thing: check if a direct lookup of 'seite__range' is possible.
        data = {'seite__range': ['1', '2']}
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertIn('seite__range', filter_params)
        self.assertEqual(filter_params['seite__range'], [1, 2])
        
    def test_get_filters_params_range_skipped_when_empty(self):
        form_class =  search_forms.SearchFormFactory()(self.model, fields = ['seite__range'])
        data = {'seite__range_0': None, 'seite__range_1': None}
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertFalse(filter_params)        
        
    def test_get_filters_params_replaces_range(self):
        # Assert that get_filter_params replaces a range query with...
        # with a query for exact when 'end' is 'empty'
        form_class =  search_forms.SearchFormFactory()(self.model, fields = ['seite__range'])
        
        data = {'seite__range_0': '1', 'seite__range_1': None}
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite', filter_params)
        
        # with a query for lte when 'start' is 'empty'
        data = {'seite__range_0': None, 'seite__range_1': '1'}
        form = form_class(data = data)
        self.assertTrue(form.is_valid(), msg = form.errors)
        filter_params = form.get_filter_params()
        self.assertNotIn('seite__range', filter_params)
        self.assertIn('seite__lte', filter_params)
