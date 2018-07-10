from .base import *

from DBentry.forms import *
from DBentry.ac.widgets import EasyWidgetWrapper, MIZModelSelect2

class TestFormBase(ModelFormTestCase):
    
    form_class = FormBase
    model = land
    fields = ['land_name', 'code']
    raw_data = [{'land_name':'Deutschland', 'code':'DE'}]
    
    def test_validate_unique(self):
        kwargs = {'instance':self.obj1, 'data' : dict(land_name=self.obj1.land_name, code=self.obj1.code)}
        form = self.get_form(**kwargs)
        self.assertTrue(form.is_valid())
        self.assertFalse(form.errors)
        
        # attempt to create a duplicate of a unique, by passing in the same data without the instance
        kwargs.pop('instance')
        form = self.get_form(**kwargs)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors)
        # validate_unique should now set the DELETE flag in cleaned_data
        form.validate_unique()
        self.assertEqual(form.cleaned_data.get('DELETE', False), True) 
        
    def test_makeForm(self):
        # makeForm should add dal widgets for foreign fields
        form = makeForm(audio)
        self.assertIsInstance(form.base_fields['sender'].widget, MIZModelSelect2)
        
        # makeForm should override the widget attrs of a TextField model field
        attrs = form.base_fields['beschreibung'].widget.attrs
        self.assertEqual(attrs['rows'], ATTRS_TEXTAREA['rows'])
        self.assertEqual(attrs['cols'], ATTRS_TEXTAREA['cols'])
        attrs = form.base_fields['bemerkungen'].widget.attrs
        self.assertEqual(attrs['rows'], ATTRS_TEXTAREA['rows'])
        self.assertEqual(attrs['cols'], ATTRS_TEXTAREA['cols'])
        
        # makeForm should respect a given 'fields' parameter
        form = makeForm(audio, fields = ['titel'])
        self.assertIn('titel', form.base_fields)
        self.assertNotIn('sender', form.base_fields)
        self.assertNotIn('tracks', form.base_fields)
        
        # makeForm should return any form classes that are already present in DBentry.forms
        # DBentry.forms.ArtikelForm overrides ATTRS_TEXTAREA for field 'schlagzeile' with {'rows':2, 'cols':90}
        form = makeForm(artikel)
        attrs = form.base_fields['schlagzeile'].widget.attrs
        self.assertEqual(attrs['rows'], 2)
        self.assertEqual(attrs['cols'], 90)
        
        
class TestInLineAusgabeForm(ModelFormTestCase):
    
    form_class = InLineAusgabeForm
    model = ausgabe.audio.through
    fields = ['ausgabe']
    test_data_count = 1
        
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
        self.assertIsInstance(form.fields['magazin'].widget, EasyWidgetWrapper)
        
class TestArtikelForm(ModelFormTestCase):
    
    form_class = ArtikelForm
    model = artikel
    fields = ['ausgabe', 'schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen']
    test_data_count = 1
    
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
        self.assertIsInstance(form.fields['magazin'].widget, EasyWidgetWrapper)
        
class TestAutorForm(ModelFormTestCase):
    form_class = AutorForm
    fields = ['person', 'kuerzel']
    model = autor
    
    def test_clean(self):
        # clean should raise a ValidationError if either kuerzel or person data is missing
        p = make(person)
        
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
        
class TestBuchForm(ModelFormTestCase):
    form_class = BuchForm
    fields = ['is_buchband', 'buchband']
    model = buch
    
    def test_clean(self):
        # clean should raise a ValidationError if both is_buchband and buchband data is present
        b = make(buch, is_buchband = True)
        
        form = self.get_form(data={'is_buchband':True, 'buchband':b.pk})
        form.full_clean()
        with self.assertRaises(ValidationError):
            form.clean()
        
        form = self.get_form(data={'is_buchband':True})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'buchband':b.pk})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
class TestHerausgeberForm(ModelFormTestCase):
    form_class = HerausgeberForm
    fields = ['person', 'organisation']
    model = Herausgeber
    
    def test_clean(self):
        p = make(person)
        o = make(Organisation)
        
        form = self.get_form(data={})
        form.full_clean()
        with self.assertRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'organisation':o.pk})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'person':p.pk})
        form.full_clean()
        with self.assertNotRaises(ValidationError):
            form.clean()
            
        form = self.get_form(data={'organisation':o.pk, 'person':p.pk})
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
  
        
class TestDynamicChoiceForm(TestDataMixin, FormTestCase):
    
    form_class = DynamicChoiceForm
    dummy_fields = {
        'cf' : forms.ChoiceField(choices = []), 
        'cf2' : forms.ChoiceField(choices = [])
    }
    model = genre
    test_data_count = 3
    
    def test_init(self):
        # choices is list of iterables with len == 2 - ideal case
        choices = [('1', '1'), ('2', '3'), ('3', '0')]
        form = self.get_dummy_form(choices=choices)
        self.assertListEqualSorted(form.fields['cf'].choices, choices)
        self.assertListEqualSorted(form.fields['cf2'].choices, choices)
        
        # choices is a list of iterables of len == 1
        choices = ['1', '2', '3']
        expected = [('1', '1'), ('2', '2'), ('3', '3')]
        form = self.get_dummy_form(choices=choices)
        self.assertListEqualSorted(form.fields['cf'].choices, expected)
        self.assertListEqualSorted(form.fields['cf2'].choices, expected)
        
        # choices is a list of objects that are not iterable
        expected = [(str(o), str(o)) for o in self.test_data]
        form = self.get_dummy_form(choices=self.test_data)
        self.assertListEqualSorted(form.fields['cf'].choices, expected)
        self.assertListEqualSorted(form.fields['cf2'].choices, expected)
        
        # choices is a dict
        choices = {'cf':['1', '2', '3'], 'cf2':self.test_data}
        form = self.get_dummy_form(choices=choices)
        self.assertListEqualSorted(form.fields['cf'].choices, [('1', '1'), ('2', '2'), ('3', '3')])
        self.assertListEqualSorted(form.fields['cf2'].choices, expected)
        
        # choices is a BaseManager
        expected = [(str(o.pk), str(o)) for o in self.test_data]
        form = self.get_dummy_form(choices=genre.objects)
        self.assertListEqualSorted(form.fields['cf'].choices, expected)
        self.assertListEqualSorted(form.fields['cf2'].choices, expected)
        
        # choices is a QuerySet
        expected = [(str(o.pk), str(o)) for o in self.test_data[:2]]
        form = self.get_dummy_form(choices=genre.objects.filter(pk__in=[pk for pk, o in expected]))
        self.assertListEqualSorted(form.fields['cf'].choices, expected)
        self.assertListEqualSorted(form.fields['cf2'].choices, expected)
        
        # preset choices are preserved
        fields = {
            'cf' : forms.ChoiceField(choices = []), 
            'cf2' : forms.ChoiceField(choices = [('1', 'a')])
        }
        choices = ['1', '2', '3']
        expected = [('1', '1'), ('2', '2'), ('3', '3')]
        form = self.get_dummy_form(fields = fields, choices=choices)
        self.assertListEqualSorted(form.fields['cf'].choices, expected)
        self.assertListEqualSorted(form.fields['cf2'].choices, [('1', 'a')])
    
class TestDynamicChoiceFormSet(FormTestCase):
    
    def test_get_form_kwargs(self):
        pass
    
