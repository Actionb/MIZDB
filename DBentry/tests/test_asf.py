import dal

from .base import *

from DBentry.advsfforms import *
from DBentry.admin import *

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
    
    def test_factory(self):
        self.assertFormChecksOut(self.expected_fields, self.expected_labels, self.expected_models)
            
    def assertFormChecksOut(self, expected_fields=None, expected_labels=None, expected_models=None, msg=None):
        expected_fields = expected_fields or self.expected_fields
        expected_labels = expected_labels or self.expected_labels
        expected_models = expected_models or self.expected_models
        model_admin = self.model_admin
        labels = model_admin.advanced_search_form.get('labels', {})
        form = advSF_factory(model_admin, labels=labels)()
        self.assertEqual(sorted(list(form.fields)), sorted(list(expected_fields)))  # TODO: use assertListsEqualSorted
        for field_path, formfield in form.fields.items():
            self.assertTrue(field_path in expected_fields, msg=field_path)
            self.assertEqual(formfield.label, expected_labels[field_path], msg=field_path)
            widget = formfield.widget
            self.assertWidgetOfDAL(widget, msg=field_path)
            self.assertWidgetCannotCreate(widget, msg=field_path)
            self.assertWidgetQSModel(widget, expected_models[field_path], msg=field_path)
    
    def assertWidgetOfDAL(self, widget, msg=None):
        self.assertIsInstance(widget, dal.widgets.QuerySetSelectMixin, msg)
    
    def assertWidgetCannotCreate(self, widget, msg=None):
        from django.urls import resolve
        view_initkwargs = resolve(widget.url).func.view_initkwargs
        self.assertFalse('create_field' in view_initkwargs, msg)
        
    def assertWidgetQSModel(self, widget, model, msg=None):
        self.assertEqual(widget.choices.queryset.model, model, msg)

class TestFactory(MyTestCase):
    # advSF_factory requires a ModelAdmin **instance**:
    # it accesses model_admin.model, and that model attribute does not exist before instantiation.
    
    def test_factory_with_m2o_field_bug(self):
        # Bug:
        # the factory will try get the verbose_name of the field -- and ManyToOneFields do not have that attribute.
        # AND later on it will call formfield() --  ManyToOneFields do not have that either!
        model_admin = PersonAdmin(person, miz_site)
        model_admin.advanced_search_form = {
            'selects' : ['herkunft', 'herkunft__land', 'herkunft__bland', 'musiker']
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
        model_admin = PersonAdmin(person, miz_site)
        model_admin.advanced_search_form = {
            'selects' : ['herkunft', 'beschreibung']
        }
        form = advSF_factory(model_admin)()
        self.assertFalse('beschreibung' in form.fields)
        self.assertTrue('herkunft' in form.fields)
        
    def test_factory_applies_forward(self):
        # Test that forwarding is applied when possible (here: bland -> land)
        model_admin = PersonAdmin(person, miz_site)
        form = advSF_factory(model_admin)()
        widget = form.fields['herkunft__bland'].widget
        self.assertEqual(widget.forward, ['herkunft__land'])
        self.assertEqual(widget.attrs.get('data-placeholder', ''), 'Bitte zuerst ein Land auswählen!')
    
class TestFactoryArtikel(FactoryTestCaseMixin,MyTestCase):
    model = artikel
    model_admin_class = ArtikelAdmin
    expected_fields = ['ausgabe__magazin', 'ausgabe', 'schlagwort', 'genre', 'band', 'musiker', 'autor']
    expected_labels = {'ausgabe__magazin':'Magazin', 'ausgabe':'Ausgabe', 'schlagwort':'Schlagwort', 'genre':'Genre', 'band':'Band', 'musiker':'Musiker', 'autor':'Autor'}
    expected_models = {'ausgabe__magazin': magazin, 'ausgabe': ausgabe, 'schlagwort': schlagwort, 'genre': genre, 'band': band, 'musiker': musiker, 'autor': autor}
    
class TestFactoryAudio(FactoryTestCaseMixin,MyTestCase):
    model = audio
    model_admin_class = AudioAdmin
    expected_fields = ['musiker', 'band', 'genre', 'spielort', 'veranstaltung', 'plattenfirma', 
                        'format__format_size', 'format__format_typ', 'format__tag']
    expected_labels = {'musiker': 'Musiker', 'band': 'Band', 'genre': 'Genre', 'spielort': 'Spielort', 'veranstaltung': 'Veranstaltung', 'plattenfirma': 'Plattenfirma', 
                        'format__format_size': 'Format größe', 'format__format_typ': 'Format typ' , 'format__tag': 'Tags'}
    expected_models = {'musiker': musiker, 'band': band, 'genre': genre, 'spielort': spielort, 'veranstaltung': veranstaltung, 'plattenfirma': plattenfirma, 
                        'format__format_size': FormatSize, 'format__format_typ': FormatTyp, 'format__tag': FormatTag}
    
class TestFactoryAusgabe(FactoryTestCaseMixin,MyTestCase):
    model = ausgabe
    model_admin_class = AusgabenAdmin
    expected_fields = ['magazin']
    expected_labels = {'magazin': 'Magazin'}
    expected_models = {'magazin': magazin}
    
class TestFactoryAutor(FactoryTestCaseMixin,MyTestCase):
    model = autor
    model_admin_class = AutorAdmin
    expected_fields = ['magazin']
    expected_labels = {'magazin': 'Magazin'}
    expected_models = {'magazin': magazin}
    
class TestFactoryBand(FactoryTestCaseMixin,MyTestCase):
    model = band
    model_admin_class = BandAdmin
    expected_fields = ['musiker', 'genre', 'herkunft__land', 'herkunft']
    expected_labels = {'musiker':'Mitglied', 'genre':'Genre', 'herkunft__land':'Herkunftsland', 'herkunft':'Herkunftsort'}
    expected_models = {'musiker': musiker, 'genre': genre, 'herkunft__land': land, 'herkunft': ort}
    
class TestFactoryMagazin(FactoryTestCaseMixin,MyTestCase):
    model = magazin
    model_admin_class = MagazinAdmin
    expected_fields = ['ort__land']
    expected_labels = {'ort__land':'Herausgabeland'}
    expected_models = {'ort__land':land}
    
class TestFactoryMusiker(FactoryTestCaseMixin,MyTestCase):
    model = musiker
    model_admin_class = MusikerAdmin
    expected_fields = ['person', 'genre', 'band', 
                'instrument','person__herkunft__land', 'person__herkunft']
    expected_labels = {'person':'Person', 'genre': 'Genre', 'band': 'Band', 
                'instrument': 'Instrument','person__herkunft': 'Herkunft', 'person__herkunft__land':'Herkunftsland'}
    expected_models = {'person':person, 'genre':genre, 'band':band,'instrument': instrument,
        'person__herkunft__land':land, 'person__herkunft':ort}
            
class TestFactoryPerson(FactoryTestCaseMixin,MyTestCase):
    model = person
    model_admin_class = PersonAdmin
    expected_fields = ['herkunft', 'herkunft__land', 'herkunft__bland']
    expected_labels = {'herkunft':'Herkunft', 'herkunft__land':'Land', 'herkunft__bland':'Bundesland'}
    expected_models = {'herkunft': ort, 'herkunft__land': land, 'herkunft__bland': bundesland}
    
class TestFactoryVerlag(FactoryTestCaseMixin,MyTestCase):
    model = verlag
    model_admin_class = VerlagAdmin
    expected_fields = ['sitz','sitz__land', 'sitz__bland']
    expected_labels = {'sitz':'Sitz','sitz__land':'Land', 'sitz__bland':'Bundesland'}
    expected_models = {'sitz':ort,'sitz__land':land, 'sitz__bland':bundesland}
    
class TestFactoryBland(FactoryTestCaseMixin,MyTestCase):
    model = bundesland
    model_admin_class = BlandAdmin
    expected_fields = ['ort__land']
    expected_labels = {'ort__land':'Land'}
    expected_models = {'ort__land':land}
    
class TestFactoryOrt(FactoryTestCaseMixin,MyTestCase):
    model = ort
    model_admin_class = OrtAdmin
    expected_fields = ['land', 'bland']
    expected_labels = {'land':'Land', 'bland':'Bundesland'}
    expected_models = {'land':land, 'bland':bundesland}
    
class TestFactoryBestand(FactoryTestCaseMixin,MyTestCase):
    model = bestand
    model_admin_class = BestandAdmin
    expected_fields = ['lagerort']
    expected_labels = {'lagerort':'Lagerort'}
    expected_models = {'lagerort':lagerort}
