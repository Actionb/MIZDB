from .base import *

from DBentry.forms import *

class TestFormBase(ModelFormTestCase):
    
    form_class = FormBase
    model = land
    fields = ['land_name', 'code']
    test_data_count = 0
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = land.objects.create(land_name='Deutschland', code='DE')
        super().setUpTestData()
        
    def test_validate_unique(self):
        kwargs = {'instance':self.obj1, 'data' : dict(land_name=self.obj1.land_name, code=self.obj1.code)}
        form = self.get_form(**kwargs)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.errors)
        
        # attempt to create a duplicate of a unique
        kwargs = {'data' : dict(land_name=self.obj1.land_name, code=self.obj1.code)}
        form = self.get_form(**kwargs)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)
        # validate_unique should now set the DELETE flag in cleaned_data
        form.validate_unique()
        self.assertEqual(form.cleaned_data.get('DELETE', False), True) 
        
class TestInLineAusgabeForm(ModelFormTestCase):
    
    form_class = InLineAusgabeForm
    model = ausgabe.audio.through
    fields = ['ausgabe']
        
    def test_init_initial_magazin(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance':self.obj1}
        form = self.get_form(**kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('magazin'), self.obj1.ausgabe.magazin)
        
    def test_form_widgets(self):
        form = self.get_form()
        self.assertTrue('ausgabe' in form.fields)
        self.assertIsInstance(form.fields['ausgabe'].widget, autocomplete.ModelSelect2)
        self.assertTrue('magazin' in form.fields)
        from DBentry.ac.widgets import EasyWidgetWrapper
        self.assertIsInstance(form.fields['magazin'].widget, EasyWidgetWrapper)
        
class TestArtikelForm(ModelFormTestCase):
    
    form_class = ArtikelForm
    model = artikel
    fields = ['ausgabe', 'schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen'] #NOTE: why not __all__?
    
    def test_init_initial_magazin(self):
        # test if initial for ausgabe.magazin is set properly during init
        kwargs = {'instance':self.obj1}
        form = self.get_form(**kwargs)
        self.assertEqual(form.instance, self.obj1)
        self.assertEqual(form.initial.get('magazin'), self.obj1.ausgabe.magazin)
        
    def test_form_widgets(self):
        form = self.get_form()
        
        self.assertTrue('schlagzeile' in form.fields)
        w = form.fields['schlagzeile'].widget
        self.assertIsInstance(w, forms.Textarea)
        self.assertEqual(w.attrs['rows'], 2)
        self.assertEqual(w.attrs['cols'], 90)
        
        self.assertTrue('zusammenfassung' in form.fields)
        self.assertIsInstance(form.fields['zusammenfassung'].widget, forms.Textarea)
        self.assertTrue('beschreibung' in form.fields)
        self.assertIsInstance(form.fields['beschreibung'].widget, forms.Textarea)
        self.assertTrue('bemerkungen' in form.fields)
        self.assertIsInstance(form.fields['bemerkungen'].widget, forms.Textarea)
        self.assertTrue('ausgabe' in form.fields)
        self.assertIsInstance(form.fields['ausgabe'].widget, autocomplete.ModelSelect2)
        self.assertTrue('magazin' in form.fields)
        from DBentry.ac.widgets import EasyWidgetWrapper
        self.assertIsInstance(form.fields['magazin'].widget, EasyWidgetWrapper)
        
class TestAutorForm(ModelFormTestCase):
    form_class = AutorForm
    fields = ['person', 'kuerzel']
    model = autor
    test_data_count = 0
    
    def test_clean(self):
        # clean should raise a ValidationError if either kuerzel or person data is missing
        p = person.objects.create(vorname='Alice', nachname='Tester')
        
        form = self.get_form(data={'beschreibung':'Boop'})
        form.full_clean()
        with self.assertRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'kuerzel':'Beep'})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'person':p.pk})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'kuerzel':'Beep', 'person':p.pk})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
        
class TestMIZAdminForm(FormTestCase):
    
    form_class = MIZAdminForm
    dummy_fields = {
        'some_int' : forms.IntegerField(), 
        'wrap_me' : forms.CharField(widget=autocomplete.ModelSelect2(url='acmagazin')), 
    }
        
    def test_iter(self):
        form = self.get_dummy_form()
        from django.contrib.admin.helpers import Fieldset 
        from DBentry.helper import MIZFieldset
        for fs in form:
            self.assertIsInstance(fs, Fieldset)
            self.assertIsInstance(fs, MIZFieldset)
            
    def test_media_prop(self):
        # Make sure jquery loaded in the right order
        media = self.get_dummy_form().media
        extra = '' if settings.DEBUG else '.min' 
        self.assertTrue('admin/js/jquery.init.js' in media._js)
        self.assertTrue('admin/js/vendor/jquery/jquery%s.js' % extra in media._js)
        self.assertEqual(media._js.index('admin/js/vendor/jquery/jquery%s.js' % extra), 0)
        self.assertEqual(media._js.index('admin/js/jquery.init.js'), 1)
        
    def test_changed_data_prop_no_change(self):
        kwargs = dict(data=dict(some_int='10'), initial=dict(some_int='10'))
        form = self.get_dummy_form(**kwargs)
        self.assertFalse(form.changed_data)
        
    def test_changed_data_prop_change(self):
        kwargs = dict(data=dict(some_int='11'), initial=dict(some_int='10'))
        form = self.get_dummy_form(**kwargs)
        self.assertTrue(form.changed_data)
  
        
class TestDynamicChoiceForm(FormTestCase):
    
    def test_init(self):
        pass
    
class TestDynamicChoiceFormSet(FormTestCase):
    
    def test_get_form_kwargs(self):
        pass
    
