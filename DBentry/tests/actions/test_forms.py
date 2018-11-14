from .base import *

from DBentry.actions.forms import makeSelectionForm, BrochureActionForm
from DBentry.ac.widgets import EasyWidgetWrapper

class TestSelectionForm(TestCase):
    
    def test(self):
        model = ausgabe
        fields = ['jahrgang', 'magazin', 'bestand__lagerort']
        formfield_classes = {'jahrgang' : forms.CharField}
        form = makeSelectionForm(model, fields, formfield_classes = formfield_classes)
        self.assertEqual(len(form.base_fields), len(fields))
        
        widget = form.base_fields['magazin'].widget
        self.assertIsInstance(widget, EasyWidgetWrapper)
        
        self.assertIsInstance(form.base_fields['jahrgang'], forms.CharField)
        
class TestBrochureActionForm(FormTestCase):
    
    form_class = BrochureActionForm

    def test_init_disables_delete_magazin(self):
        # Assert that init disables the field delete_magazin if the magazin cannot be deleted
        mag = make(magazin)
        a1, a2 = batch(ausgabe, 2, magazin = mag)
        
        form = self.get_form(initial = {'ausgabe_id': a1.pk})
        self.assertTrue(form.fields['delete_magazin'].disabled)
        
        a2.delete()
        form = self.get_form(initial = {'ausgabe_id': a1.pk})
        self.assertFalse(form.fields['delete_magazin'].disabled)
        
    
