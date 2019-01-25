from .base import MyTestCase

from django import forms

from DBentry.models import ausgabe
from DBentry.actions.forms import makeSelectionForm
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
