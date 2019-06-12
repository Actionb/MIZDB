import dal
from unittest.mock import Mock

from django.utils.datastructures import MultiValueDict
from django.contrib.admin.utils import get_fields_from_path
from django.utils.translation import override as translation_override
from django.test import tag

from .base import MyTestCase, FormTestCase

import DBentry.models as _models
from DBentry.advsfforms import AdvSFForm, advSF_factory
from DBentry.admin import (
    ArtikelAdmin, AudioAdmin, AusgabenAdmin, AutorAdmin, BandAdmin, BestandAdmin, MagazinAdmin, MusikerAdmin, 
    OrtAdmin, VerlagAdmin, PersonAdmin, BlandAdmin
)
from DBentry.sites import miz_site
from DBentry.factory import make

from dal import forward

class FactoryTestCaseMixin(object):
    
    admin_site = miz_site
    model = None
    model_admin_class = None
    expected_fields = []
    expected_labels = {}
    expected_models = {}
    
    def setUp(self):
        super().setUp()
        self.model_admin = self.model_admin_class(self.model, self.admin_site)

        
    def get_expected_fields(self):
        # Return the field_paths for any relation field declared in advanced_search_form['selects'] 
        # whose formfield requires a dal autocomplete widget
        expected_fields = set()  
        for field_path in self.model_admin.advanced_search_form.get('selects', []):
            if isinstance(field_path, (tuple, list)):
                # This field_path is a tuple of (field_path, dal forward widget name)
                field_path = field_path[0]
            if get_fields_from_path(self.model, field_path)[-1].is_relation:
                # This field path points to a relation field and thus requires a dal widget
                expected_fields.add(field_path)
        return list(expected_fields)
        
    def get_expected_models(self):
        # Return the related models for any relation field declared in advanced_search_form['selects']
        expected_models = {}
        for field_path in self.model_admin.advanced_search_form.get('selects', []):
            if isinstance(field_path, (tuple, list)):
                # This field_path is a tuple of (field_path, dal forward widget name)
                field_path = field_path[0]
            expected_models[field_path] = get_fields_from_path(self.model, field_path)[-1].related_model
        return expected_models
    
    def test_factory(self):
        # Assert that advSF_factory creates all the relational formfields correctly
        expected_fields = self.get_expected_fields()
        expected_models = self.get_expected_models()
        form = advSF_factory(self.model_admin, labels=self.model_admin.advanced_search_form.get('labels', {}))()
        
        # check the widgets
        for field_path, formfield in form.fields.items():
            self.assertIn(field_path, expected_fields, msg=field_path)
            expected_fields.remove(field_path)
            self.assertIn(field_path, self.expected_labels, msg= "Label not found for. Please check the TestCase's expected_labels.")
            self.assertEqual(formfield.label, self.expected_labels[field_path], msg=field_path)
            widget = formfield.widget
            self.assertIsInstance(widget, dal.widgets.QuerySetSelectMixin, msg=field_path)
            self.assertWidgetCannotCreate(widget, msg=field_path)
            # Check that the widget queries the right model
            self.assertEqual(widget.choices.queryset.model, expected_models[field_path], msg=field_path)
        # Check that all fields in expected_fields have been used in the form
        self.assertFalse(expected_fields, msg = "\n Select fields are missing from search form: " + str(expected_fields))
    
    def assertWidgetCannotCreate(self, widget, msg=None):
        # Assert that the widget cannot create new records, this is indicated by the widget's view not having a create_field
        from django.urls import resolve
        view_initkwargs = resolve(widget.url).func.view_initkwargs
        self.assertFalse('create_field' in view_initkwargs, msg)


class TestFactory(MyTestCase):
    # advSF_factory requires a ModelAdmin **instance**:
    # it accesses model_admin.model, and that model attribute does not exist before instantiation.
    
    @translation_override(language = None)
    def test_exceptions(self):
        # Assert that the correct exceptions are raised.
        with self.assertRaises(TypeError, msg = "A subclass of ModelAdmin is required.") as context_manager:
            advSF_factory(model_admin = object())
        self.assertEqual("object class must be a subclass of ModelAdmin.", context_manager.exception.args[0])
        
        with self.assertRaises(TypeError, msg = "A ModelAdmin instance is required.") as context_manager:
            advSF_factory(model_admin = PersonAdmin)
        self.assertEqual("model_admin argument must be a ModelAdmin instance.", context_manager.exception.args[0])
        
    
    @tag("bugfix")
    def test_factory_with_m2o_field_bug(self):
        # Bug:
        # the factory will try get the verbose_name of the field -- and ManyToOneFields do not have that attribute.
        # AND later on it will call formfield() --  ManyToOneFields do not have that either!
        model_admin = PersonAdmin(_models.person, miz_site)
        model_admin.advanced_search_form = {
            'selects' : ['musiker']
        }
        
        with self.assertNotRaises(AttributeError):
            form_class = advSF_factory(model_admin, labels={'musiker':'beep'})
        self.assertEqual(form_class().fields['musiker'].label, 'beep')
        with self.assertNotRaises(AttributeError):
            form_class = advSF_factory(model_admin)
        self.assertEqual(form_class().fields['musiker'].label, 'Musiker')
        
    def test_factory_ignores_non_relation_fields(self):
        # The factory is meant to provide autocomplete functionality to the AdvSF. 
        # Basic fields that do not represent a relation do not need this.
        # Sneak in a non-relation field into 'selects'.
        model_admin = PersonAdmin(_models.person, miz_site)
        model_admin.advanced_search_form = {
            'selects' : ['orte', 'beschreibung']
        }
        form = advSF_factory(model_admin)()
        self.assertFalse('beschreibung' in form.fields)
        self.assertTrue('orte' in form.fields)
    
    @translation_override(language = None)
    def test_factory_applies_forward(self):
        # Test that forwarding is applied when possible (here: 'selects' : ['orte', 'orte__land', ('orte__bland', 'orte__land')]
        model_admin = PersonAdmin(_models.person, miz_site)
        form = advSF_factory(model_admin)()
        widget = form.fields['orte__bland'].widget
        forwarded = widget.forward[0]

        self.assertIsInstance(forwarded, forward.Field)
        self.assertEqual(forwarded.src, 'orte__land')
        self.assertEqual(forwarded.dst, 'land')
        self.assertEqual(widget.attrs.get('data-placeholder', ''), 'Bitte zuerst Land auswählen.')
    
class TestFactoryArtikel(FactoryTestCaseMixin,MyTestCase):
    model = _models.artikel
    model_admin_class = ArtikelAdmin
    expected_labels = {'ausgabe__magazin':'Magazin', 'ausgabe':'Ausgabe', 'schlagwort':'Schlagwort', 'genre':'Genre', 'band':'Band', 'musiker':'Musiker', 'autor':'Autor'}
    
class TestFactoryAudio(FactoryTestCaseMixin,MyTestCase):
    model = _models.audio
    model_admin_class = AudioAdmin
    expected_labels = {'musiker': 'Musiker', 'band': 'Band', 'genre': 'Genre', 'spielort': 'Spielort', 'veranstaltung': 'Veranstaltung', 'plattenfirma': 'Plattenfirma', 
                        'format__format_size': 'Format Größe', 'format__format_typ': 'Format Typ' , 'format__tag': 'Tags'}
                        
class TestFactoryAusgabe(FactoryTestCaseMixin,MyTestCase):
    model = _models.ausgabe
    model_admin_class = AusgabenAdmin
    expected_labels = {'magazin': 'Magazin'}
    
class TestFactoryAutor(FactoryTestCaseMixin,MyTestCase):
    model = _models.autor
    model_admin_class = AutorAdmin
    expected_labels = {'magazin': 'Magazin'}
    
class TestFactoryBand(FactoryTestCaseMixin,MyTestCase):
    model = _models.band
    model_admin_class = BandAdmin
    expected_labels = {'musiker':'Mitglied', 'genre':'Genre', 'orte__land':'Land', 'orte':'Ort'}

class TestFactoryMagazin(FactoryTestCaseMixin,MyTestCase):
    model = _models.magazin
    model_admin_class = MagazinAdmin
    expected_labels = {'m2m_magazin_verlag':'Verlag', 'm2m_magazin_herausgeber': 'Herausgeber', 'ort': 'Herausgabeort', 'genre':'Genre'}
    
class TestFactoryMusiker(FactoryTestCaseMixin,MyTestCase):
    model = _models.musiker
    model_admin_class = MusikerAdmin
    expected_labels = {'person':'Person', 'genre': 'Genre', 'band': 'Band', 
                'instrument': 'Instrument','orte': 'Ort', 'orte__land':'Land'}
            
class TestFactoryPerson(FactoryTestCaseMixin,MyTestCase):
    model = _models.person
    model_admin_class = PersonAdmin
    expected_labels = {'orte':'Ort', 'orte__land':'Land', 'orte__bland':'Bundesland'}
    
class TestFactoryVerlag(FactoryTestCaseMixin,MyTestCase):
    model = _models.verlag
    model_admin_class = VerlagAdmin
    expected_labels = {'sitz':'Sitz','sitz__land':'Land', 'sitz__bland':'Bundesland'}
    
class TestFactoryBland(FactoryTestCaseMixin,MyTestCase):
    model = _models.bundesland
    model_admin_class = BlandAdmin
    expected_labels = {'ort__land':'Land'}
    
class TestFactoryOrt(FactoryTestCaseMixin,MyTestCase):
    model = _models.ort
    model_admin_class = OrtAdmin
    expected_labels = {'land':'Land', 'bland':'Bundesland'}
    
class TestFactoryBestand(FactoryTestCaseMixin,MyTestCase):
    model = _models.bestand
    model_admin_class = BestandAdmin
    expected_labels = {'lagerort':'Lagerort'}


class TestAdvSFForm(FormTestCase):
    
    form_class = AdvSFForm
    
    def test_get_initial_for_field_MultiValueDict(self):
        # Assert that get_initial_for_field accepts and handles a MultiValueDict as initial
        form = self.get_form()
        form.initial = MultiValueDict({'Test':[1, 2, 3]})
        mock_field = Mock()
        self.assertEqual(form.get_initial_for_field(field = mock_field, field_name = 'Test'), [1, 2, 3])   
        
    def test_get_initial_for_field_ausgabe_magazin(self):
        # Assert that an initial value for a 'magazin' formfield is assigned from a present initial value for 'ausgabe'
        obj = make(_models.ausgabe)
        form = self.get_form()
        mock_field = Mock(initial = 'Mocked Initial')
        mock_field.spec_set = True
        self.assertEqual(form.get_initial_for_field(mock_field, 'ausgabe__magazin'), 'Mocked Initial')
        form.initial = {'ausgabe':obj.pk}
        self.assertEqual(form.get_initial_for_field(mock_field, 'ausgabe__magazin'), obj.magazin)
        # Make sure DoesNotExist exceptions bubble up to the surface
        form.initial = {'ausgabe':None}
        self.assertEqual(form.get_initial_for_field(mock_field, 'ausgabe__magazin'), 'Mocked Initial')
