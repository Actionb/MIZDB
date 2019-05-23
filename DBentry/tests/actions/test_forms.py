from ..base import MyTestCase, FormTestCase

from django import forms
from django.core.exceptions import ValidationError

from DBentry.models import ausgabe
from DBentry.actions.forms import makeSelectionForm, BrochureActionFormOptions
from DBentry.ac.widgets import EasyWidgetWrapper

class TestSelectionForm(MyTestCase):
    
    def test(self):
        model = ausgabe
        fields = ['jahrgang', 'magazin', 'bestand__lagerort']
        formfield_classes = {'jahrgang' : forms.CharField}
        form = makeSelectionForm(model, fields, formfield_classes = formfield_classes)
        self.assertEqual(len(form.base_fields), len(fields))
        
        widget = form.base_fields['magazin'].widget
        self.assertIsInstance(widget, EasyWidgetWrapper)
        
        self.assertIsInstance(form.base_fields['jahrgang'], forms.CharField)
        
class TestBrochureActionFormOptions(FormTestCase):
    
    form_class = BrochureActionFormOptions
    
    def test_clean_brochure_art(self):
        form = self.get_form()
        form.cleaned_data = {'brochure_art': 'INVALID'}
        with self.assertRaises(ValidationError):
            form.clean_brochure_art()
        
        form.cleaned_data['brochure_art'] = 'Katalog'
        with self.assertNotRaises(ValidationError):
            form.clean_brochure_art()
