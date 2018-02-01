from .base import *

from DBentry.actions.forms import makeSelectionForm

class TestSelectionForm(TestCase):
    
    def test(self):
        model = ausgabe
        fields = ['jahrgang', 'magazin', 'bestand__lagerort']
        formfield_classes = {'jahrgang' : forms.CharField}
        form = makeSelectionForm(model, fields, formfield_classes = formfield_classes)
        self.assertEqual(len(form.base_fields), len(fields))
        
        from dal import autocomplete
        widget = form.base_fields['magazin'].widget
        self.assertIsInstance(widget, autocomplete.ModelSelect2)
        self.assertEqual(widget._url,'acmagazin_nocreate')
        
        self.assertIsInstance(form.base_fields['jahrgang'], forms.CharField)
