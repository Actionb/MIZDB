from ..base import  FormTestCase

from django.core.exceptions import ValidationError

from DBentry.actions.forms import BrochureActionFormOptions
        
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
