from .base import DataTestCase, UserTestCase

from django.test import tag
from django.db import models as django_models
from django.utils.translation import override as translation_override

import DBentry.models as _models
from DBentry import fields as _fields
from DBentry.m2m import m2m_audio_musiker
from DBentry.factory import make

class TestBaseModel(DataTestCase):

    model = _models.artikel
    add_relations = True
    test_data_count = 1        

    def test_qs(self):
        self.assertIsInstance(self.obj1.qs(), django_models.QuerySet)
        self.assertEqual(self.obj1.qs().count(), 1)
        self.assertListEqualSorted(self.obj1.qs(), self.queryset.filter(pk=self.obj1.pk))

    def test_qs_exception(self):
        with self.assertRaises(AttributeError):
            self.model.qs(self.model)
            
    def test_str(self):
        # Assert that __str__ just takes the value of the name_field if available
        obj = make(_models.video, titel = "lotsa testing", tracks = 1, quelle = "from the computer")
        self.assertEqual(obj.__str__(), "lotsa testing")
        obj.name_field = "quelle"
        self.assertEqual(obj.__str__(), "from the computer")
        
        # Assert that, if no name_field is set, __str__ defaults to the old method of gathering values from applicable fields to form a string
        obj.name_field = None
        self.assertEqual(obj.__str__(), "lotsa testing 1 from the computer")
        

    def test_get_search_fields(self):
        expected = ['schlagzeile', 'zusammenfassung', 'beschreibung']
        self.assertListEqualSorted(self.model.get_search_fields(True), expected)
        
class TestBaseM2MModel(DataTestCase):
    
    model = m2m_audio_musiker
    raw_data = [
        {'audio__titel':'Testaudio', 'musiker__kuenstler_name':'Alice Test'}, 
        {'audio__titel':'Testaudio', 'musiker__kuenstler_name':'Alice Test', 'instrument__instrument':'Piano'}, 
    ]
    
    def test_str(self):
        expected = "Testaudio (Alice Test)"
        self.assertEqual(self.obj1.__str__(), expected)
        self.assertEqual(self.obj2.__str__(), expected)
    

@tag("cn")    
class TestComputedNameModel(DataTestCase):

    model = _models.ausgabe
    default = model._name_default % {'verbose_name': model._meta.verbose_name}

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.magazin)
        cls.obj1 = make(cls.model, magazin=cls.mag)
        cls.obj2 = make(cls.model, magazin=cls.mag)
        cls.test_data = [cls.obj1, cls.obj2]

        super().setUpTestData()

    def test_init(self):
        # The name should be updated upon init
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        obj = self.qs_obj1.first()
        self.assertFalse(obj._changed_flag)
        self.assertEqual(obj._name,  "Testinfo")

    def test_get_search_fields(self):
        # _name should be used in searches, that's the whole point of this endeavour
        self.assertIn('_name', self.model.get_search_fields())
        self.assertNotIn('_changed_flag', self.model.get_search_fields())

        # _name should always be the first field in search_fields
        self.model.search_fields += ['_name']
        self.assertEqual(self.model.get_search_fields()[0], '_name')

    def test_name_default(self):
        self.assertEqual(str(self.obj1), self.default)

    def test_update_name_notexplodes_on_no_pk_and_forced(self):
        # Unsaved instances should be ignored, as update_name relies on filtering queries with the instance's pk.
        obj = _models.ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name(force_update = True))

    def test_update_name_aborts_on_no_pk(self):
        # Unsaved instances should be ignored, as update_name relies on filtering queries with the instance's pk.
        obj = _models.ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name())

    def test_update_name_aborts_on_name_deferred(self):
        # Do not allow updating the name if it is deferred
        # Pretend as if '_name' is deferred by removing it from __dict__: see get_deferred_fields in django.db.models.base.py
        self.obj2.__dict__.pop('_name')
        self.assertFalse(self.obj2.update_name())

    def test_update_name_on_name_not_deferred(self):
        # Allow updating the name if it is not deferred
        # Pretend as if everything but '_name' is deferred by removing keys from __dict__: see get_deferred_fields in django.db.models.base.py
        keys_to_pop = [k for k in self.obj2.__dict__.keys() if not (k.startswith('_') or k in ('id', ))] # preserve id and private attributes
        for k in keys_to_pop:
            self.obj2.__dict__.pop(k)

        self.obj2._name = 'Beep'
        self.obj2._changed_flag = True
        self.assertTrue(self.obj2.update_name())
        self.assertEqual(self.obj2._name, self.default)

    def test_update_name_resets_change_flag(self):
        # The _changed_flag should always be set to False after an update was executed
        self.obj2._name = 'Beep'
        self.obj2._changed_flag = True
        self.assertTrue(self.obj2.update_name())
        self.assertFalse(self.obj2._changed_flag)

    def test_update_name__always_resets_change_flag(self):
        # Even if the _name does not need changing, the _changed_flag should still be set to False
        self.qs_obj1.update(_changed_flag=True)
        self.assertFalse(self.obj1.update_name())
        self.assertFalse(self.obj1._changed_flag)

    def test_update_name_does_not_update_with_no_change_flag(self):
        # An update should be skipped if the _changed_flag is False
        self.qs_obj1.update(_name='Beep')
        self.assertFalse(self.obj1.update_name())

    def test_update_name_enforces_name_composing_fields(self):
        # the attribute name_composing_fields is required
        backup = self.model.name_composing_fields.copy()
        self.model.name_composing_fields = None
        with self.assertRaises(AttributeError):
            self.obj1.update_name(force_update = True)
        self.model.name_composing_fields = backup

    def test_update_name_changed_flag_deferred(self):
        # _changed_flag attribute is deferred, instead of using refresh_from_db, get the value from the database
        obj = self.qs_obj1.defer('_changed_flag').first()
        with self.assertNumQueries(1):
            obj.update_name()

    def test_save_forces_update(self):
        # save() should update the name even if _changed_flag is False
        self.obj2.beschreibung = 'Testinfo'
        self.obj2.sonderausgabe = True
        self.obj2._changed_flag = False
        self.obj2.save()
        self.assertQSValuesList(self.qs_obj2, '_name', "Testinfo")
        self.assertEqual(self.obj2._name, "Testinfo")
        self.assertEqual(str(self.obj2), "Testinfo")


class TestModelArtikel(DataTestCase):

    model = _models.artikel
    test_data_count = 1

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), str(self.obj1.schlagzeile))
        self.obj1.schlagzeile=''
        self.assertEqual(self.obj1.__str__(), 'Keine Schlagzeile gegeben!')
        self.obj1.zusammenfassung='Dies ist eine Testzusammenfassung, die nicht besonders lang ist.'
        self.assertEqual(self.obj1.__str__(), 'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.')

class TestModelAudio(DataTestCase):

    model = _models.audio
    raw_data = [{'titel' : 'Testaudio'}]
    
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testaudio')
 
@tag("cn")        
class TestModelAusgabe(DataTestCase):

    model = _models.ausgabe

    @translation_override(language = None)
    def test_get_name(self):
        # 1. sonderausgabe + beschreibung
        # 2. !jahre + jahrgang/!jahrgang
        # 3. ausgaben_merkmal>e_datum>monat>lnum>?
        # 4. num>monat>lnum>e_datum>beschreibung>k.A.

        # sonderausgabe + beschreibung => beschreibung
        name_data = {'sonderausgabe':True, 'beschreibung':'Test-Info'}
        expected = 'Test-Info'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'sonderausgabe + beschreibung => beschreibung')
        # sonderausgabe + beschreibung + any other data => beschreibung
        name_data.update({'jahrgang':'2','ausgabe_jahr__jahr':['2020'], 'ausgabe_monat__monat__abk':['Dez']})
        expected = 'Test-Info'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'sonderausgabe + beschreibung + any other data => beschreibung')

        # with jahr:
        # monat
        name_data = {'ausgabe_jahr__jahr':['2020'], 'ausgabe_monat__monat__abk':['Dez']}
        expected = "2020-Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21 (2020)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "2020-20"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum + num => num')

        # with jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Dez'], 'jahrgang':'2'}
        expected = "Jg. 2-Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21 (Jg. 2)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "Jg. 2-20"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum + num => num')

        # without jahr or jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Dez']}
        expected = "k.A.-Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "k.A.-20"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum + num => num')

        # only beschreibung
        name_data = {'beschreibung':'Test-Info'}
        expected = 'Test-Info'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = ' only beschreibung')

        # no data whatsoever
        name_data = {}
        expected = 'No data for Ausgabe.'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat => monat')

        # Tests with an ausgaben_merkmal override set
        name_data = {
            'ausgabe_jahr__jahr':['2020'], 
            'ausgabe_monat__monat__abk':['Dez'], 
            'ausgabe_lnum__lnum':['21'], 
            'ausgabe_num__num':['20'], 
            'e_datum' : '02.05.2018', 
        }

        name_data.update({'magazin__ausgaben_merkmal':'e_datum'})
        expected = '02.05.2018'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: e_datum')

        name_data.update({'magazin__ausgaben_merkmal':'monat'})
        expected = '2020-Dez'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: monat')

        name_data.update({'magazin__ausgaben_merkmal':'num'})
        expected = '2020-20'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: num')

        name_data.update({'magazin__ausgaben_merkmal':'lnum'})
        expected = '21 (2020)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: lnum')

        name_data.update({'ausgabe_jahr__jahr':[]})
        expected = '21'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: lnum + no jahr')

        # merkmal set but the ausgabe contains no data for it
        name_data = {'magazin__ausgaben_merkmal':'num', 'beschreibung' : 'Woops!'}
        expected = 'Woops!'
        self.assertEqual(self.model._get_name(**name_data), expected)
        
        
        # And now with multiples of related objects
        # with jahr:
        # monat
        name_data = {'ausgabe_jahr__jahr':['2021', '2020'], 'ausgabe_monat__monat__abk':['Jan', 'Dez']}
        expected = "2020/21-Jan/Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat => monat')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['22', '21']})
        expected = "21/22 (2020/21)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['21', '20']})
        expected = "2020/21-20/21"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum + num => num')

        # with jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Jan', 'Dez'], 'jahrgang':'2'}
        expected = "Jg. 2-Jan/Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat => monat')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['22', '21']})
        expected = "21/22 (Jg. 2)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['21', '20']})
        expected = "Jg. 2-20/21"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum + num => num')

        # without jahr or jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Jan', 'Dez']}
        expected = "k.A.-Jan/Dez"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat => monat')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['22', '21']})
        expected = "21/22"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['21', '20']})
        expected = "k.A.-20/21"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum + num => num')

        # Tests with an ausgaben_merkmal override set
        name_data = {
            'ausgabe_jahr__jahr':['2021', '2020'], 
            'ausgabe_monat__monat__abk':['Jan', 'Dez'], 
            'ausgabe_lnum__lnum':['22', '21'], 
            'ausgabe_num__num':['21', '20'], 
        }

        name_data.update({'magazin__ausgaben_merkmal':'monat'})
        expected = '2020/21-Jan/Dez'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: monat')

        name_data.update({'magazin__ausgaben_merkmal':'num'})
        expected = '2020/21-20/21'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: num')

        name_data.update({'magazin__ausgaben_merkmal':'lnum'})
        expected = '21/22 (2020/21)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: lnum')

        name_data.update({'ausgabe_jahr__jahr':[]})
        expected = '21/22'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'merkmal: lnum + no jahr')
        
        
class TestModelAusgabeJahr(DataTestCase):
    
    model = _models.ausgabe_jahr
    
    def test_str(self):
        obj = make(self.model, jahr=2018)
        self.assertEqual(str(obj), '2018')
        
class TestModelAusgabeLnum(DataTestCase):
    
    model = _models.ausgabe_lnum
    
    def test_str(self):
        obj = make(self.model, lnum=21)
        self.assertEqual(str(obj), '21')
        
class TestModelAusgabeMonat(DataTestCase):
    
    model = _models.ausgabe_monat
    
    def test_str(self):
        obj = make(self.model, monat__monat='Dezember')
        self.assertEqual(str(obj), 'Dez')
        
class TestModelAusgabeNum(DataTestCase):
    
    model = _models.ausgabe_num
    
    def test_str(self):
        obj = make(self.model, num = 20)
        self.assertEqual(str(obj), '20')

@tag("cn") 
class TestModelAutor(DataTestCase):

    model = _models.autor

    @translation_override(language = None)
    def test_get_name(self):
        # 1. person_name + kuerzel
        # 2. person_name
        # 3. kuerzel
        # 4. cls._name_default
        name_data = {'person___name':'Alice Tester', 'kuerzel':'TK'}
        expected = 'Alice Tester (TK)'
        self.assertEqual(self.model._get_name(**name_data), expected)

        name_data = {'person___name':'Alice Tester'}
        expected = 'Alice Tester'
        self.assertEqual(self.model._get_name(**name_data), expected)

        name_data = {'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(self.model._get_name(**name_data), expected)

        name_data = {}
        expected = 'No data for Autor.'
        self.assertEqual(self.model._get_name(**name_data), expected)

        # get_name should ignore default values for person
        name_data = {'person___name':'No data for Person.', 'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(self.model._get_name(**name_data), expected)

        name_data = {'person___name':'unbekannt', 'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(self.model._get_name(**name_data), expected)

class TestModelBand(DataTestCase):

    model = _models.band
    
    def test_str(self):
        obj = make(self.model, band_name='Testband', beschreibung = 'Beep', bemerkungen = 'Boop')
        self.assertEqual(str(obj), 'Testband')
        
class TestModelBestand(DataTestCase):
    pass

class TestModelBildmaterial(DataTestCase):
    
    model = _models.bildmaterial
    
    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

class TestModelBuch(DataTestCase):
    pass
    
class TestModelBuchSerie(DataTestCase):
    pass
        
class TestModelBundesland(DataTestCase):
    
    model = _models.bundesland
    
    def test_str(self):
        obj = make(self.model, bland_name ='Hessen', code = 'HE')
        self.assertEqual(str(obj), 'Hessen HE')

class TestModelDatei(DataTestCase):

    model = _models.datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')
        
class TestModelDokument(DataTestCase):
    pass

@tag("cn") 
class TestModelFormat(DataTestCase):
    
    model = _models.Format
    
    def test_get_name(self):
        # format_typ only
        name_data = {'format_typ__typ':'Vinyl'}
        expected = 'Vinyl'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_typ only')
        
        # format_size only
        name_data = {'format_size__size':'LP'}
        expected = 'LP'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_size only')
        
        # format_size + anzahl <= 1
        name_data.update({'anzahl':1})
        expected = 'LP'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_size + anzahl <= 1')
        
        # format_size + anzahl 
        name_data.update({'anzahl':2})
        expected = '2xLP'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_size + anzahl')
        
        # format_size + anzahl + channel
        name_data.update({'channel':'Mono'})
        expected = '2xLP, Mono'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_size + anzahl + channel')
        
        # format_size + anzahl + channel + tags
        name_data.update({'tag__tag':['Compilation', 'Album']})
        expected = '2xLP, Album, Compilation, Mono'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'format_size + anzahl + channel + tags')
        
class TestModelFormatSize(DataTestCase):
    
    model = _models.FormatSize
    
    def test_str(self):
        obj = self.model(size='LP')
        self.assertEqual(str(obj), 'LP')

class TestModelFormatTag(DataTestCase):

    model = _models.FormatTag

    def test_str(self):
        obj = self.model(tag='Testtag')
        self.assertEqual(str(obj), 'Testtag')
        
class TestModelFormatTyp(DataTestCase):
    
    model = _models.FormatTyp
    
    def test_str(self):
        obj = self.model(typ='Test')
        self.assertEqual(str(obj), 'Test')
        
class TestModelGeber(DataTestCase):
    
    model = _models.geber
    
    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

class TestModelGenre(DataTestCase):

    model = _models.genre
    
    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')
   
@tag("cn")      
class TestModelHerausgeber(DataTestCase):
    
    model = _models.Herausgeber
    
    @translation_override(language = None)
    def test_get_name(self):
        name_data = {'person___name':'Alice Test', 'organisation__name':'Testorga'}
        expected = "Alice Test (Testorga)"
        self.assertEqual(self.model._get_name(**name_data), expected)
        
        name_data = {'person___name':'Alice Test'}
        expected = "Alice Test"
        self.assertEqual(self.model._get_name(**name_data), expected)
        
        name_data = {'organisation__name':'Testorga'}
        expected = "Testorga"
        self.assertEqual(self.model._get_name(**name_data), expected)
        
        
class TestModelInstrument(DataTestCase):

    model = _models.instrument

    def test_str(self):
        obj = self.model(instrument = 'Posaune', kuerzel = 'pos')
        self.assertEqual(str(obj), 'Posaune (pos)')
        
        obj = self.model(instrument = 'Posaune', kuerzel = '')
        self.assertEqual(str(obj), 'Posaune')
        
class TestModelKreis(DataTestCase):
    pass

@tag("cn") 
class TestModelLagerort(DataTestCase):

    model = _models.lagerort

    @translation_override(language = None)
    def test_get_name(self):        
        # ort only
        name_data = {'ort':'Testort'}
        expected = 'Testort'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort only')
        
        # ort + regal
        name_data.update({'regal':'Testregal'})
        expected = 'Testregal (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + regal')
        
        # ort + regal + fach
        name_data.update({'fach':'12'})
        expected = "Testregal-12 (Testort)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + regal + fach')
        
        # ort + raum
        name_data = {'ort':'Testort', 'raum':'Testraum'}
        expected = 'Testraum (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + raum')
        
        # ort + raum + regal
        name_data.update({'regal':'Testregal'})
        expected = 'Testraum-Testregal (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + raum + regal')
        
        # ort + raum + regal + fach
        name_data.update({'fach':'12'})
        expected = "Testraum-Testregal-12 (Testort)"
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + raum + regal + fach')
        
        
        
class TestModelLand(DataTestCase):
    
    model = _models.land
    
    def test_str(self):
        obj = self.model(land_name = 'Deutschland', code='DE')
        self.assertEqual(str(obj), 'Deutschland DE')

class TestModelMagazin(DataTestCase):

    model = _models.magazin
    
    def test_str(self):
        obj = self.model(magazin_name='Testmagazin')
        self.assertEqual(str(obj), 'Testmagazin')
        
class TestModelMemorabilien(DataTestCase):
    pass
        
class TestModelMonat(DataTestCase):
    
    model = _models.monat
    
    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

class TestModelMusiker(DataTestCase):

    model = _models.musiker

    def test_str(self):
        obj = self.model(kuenstler_name='Alice Tester', beschreibung = 'Beep', bemerkungen = 'Boop')
        self.assertEqual(str(obj), 'Alice Tester')
        
class TestModelNoiseRed(DataTestCase):
    
    model = _models.NoiseRed
    
    def test_str(self):
        obj = self.model(verfahren='Beepboop')
        self.assertEqual(str(obj), 'Beepboop')
 
@tag("cn")        
class TestModelOrt(DataTestCase):

    model = _models.ort
        
    @translation_override(language = None)
    def test_get_name(self):        
        # land only
        name_data = {'land__land_name':'Deutschland'}
        expected = 'Deutschland'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'land only')
        
        # land + bundesland
        name_data.update({'land__code':'DE', 'bland__bland_name':'Hessen'})
        expected = 'Hessen, DE'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'land + bundesland')
        
        # stadt + land
        name_data.update({'stadt':'Kassel'})
        expected = 'Kassel, DE'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'stadt + land')
        
        # stadt + land + bundesland
        name_data.update({'bland__code':'HE'})
        expected = 'Kassel, DE-HE'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'stadt + land + bundesland')
  
@tag("cn")       
class TestModelPerson(DataTestCase):

    model = _models.person

    @translation_override(language = None)
    def test_get_name(self):
        # no data given
        name_data = {'vorname':'', 'nachname':''}
        expected = 'No data for Person.'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'no data given')

        # nachname only
        name_data = {'vorname':'', 'nachname':'Test'}
        expected = 'Test'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'nachname only')
        
        # vorname + nachname
        name_data = {'vorname':'Beep', 'nachname':'Boop'}
        expected = 'Beep Boop'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'vorname + nachname')

class TestModelPlattenfirma(DataTestCase):
    
    model = _models.plattenfirma
    
    def test_str(self):
        obj = self.model(name='Testfirma')
        self.assertEqual(str(obj), 'Testfirma')
        
class TestModelProvenienz(DataTestCase):

    model = _models.provenienz

    def test_str(self):
        obj = make(self.model, geber__name = 'TestGeber', typ = 'Fund')
        self.assertEqual(str(obj), 'TestGeber (Fund)')
        
class TestModelSchlagwort(DataTestCase):

    model = _models.schlagwort
    
    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')
        
class TestModelSender(DataTestCase):
    
    model = _models.sender
    
    def test_str(self):
        obj = self.model(name = 'Testsender')
        self.assertEqual(str(obj), 'Testsender')
        
class TestModelSpielort(DataTestCase):
    
    model = _models.spielort
    
    def test_str(self):
        land_object = _models.land.objects.create(land_name = 'Deutschland', code='DE')
        obj = self.model(name = 'Testspielort', ort = _models.ort.objects.create(land=land_object))
        self.assertEqual(str(obj), 'Testspielort')
        
class TestModelSprache(DataTestCase):
    
    model = _models.sprache
    
    def test_str(self):
        obj = self.model(sprache = 'Deutsch', abk = 'de')
        self.assertEqual(str(obj), 'Deutsch de')
        
class TestModelTechnik(DataTestCase):
    pass
        
class TestModelVeranstaltung(DataTestCase):
    
    model = _models.veranstaltung
    
    def test_str(self):
        obj = self.model(name='Testveranstaltung')
        # __str__ should handle a 'datum' instance attribute that is not 
        # a PartialDate:
        obj.datum = '02.05.2018'
        self.assertEqual(str(obj), 'Testveranstaltung (02.05.2018)')
        
        # And it should localize the date if it is a PartialDate
        obj.datum = _fields.PartialDate.from_string('2018-05-02')
        self.assertEqual(str(obj), 'Testveranstaltung (02 Mai 2018)')
        
class TestModelVerlag(DataTestCase):
    
    model = _models.verlag
    
    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')
        
class TestModelVideo(DataTestCase):
    pass
    

class TestModelFavoriten(DataTestCase, UserTestCase):

    model = _models.Favoriten

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData() # create the users
        cls.obj1 = cls.model.objects.create(user=cls.super_user)
        genre, schlagwort = (_models.genre, _models.schlagwort)
        cls.obj1.fav_genres.add(genre.objects.create(genre='Testgenre1'))
        cls.obj1.fav_genres.add(genre.objects.create(genre='Testgenre2'))
        cls.obj1.fav_schl.add(schlagwort.objects.create(schlagwort='Testwort1'))
        cls.obj1.fav_schl.add(schlagwort.objects.create(schlagwort='Testwort2'))

        cls.test_data = [cls.obj1]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Favoriten von superuser')

    def test_get_favorites(self):
        # If no model is provided, return all favorites as a dict 
        genre, schlagwort = (_models.genre, _models.schlagwort)
        expected = {genre : self.obj1.fav_genres.all(), schlagwort : self.obj1.fav_schl.all()}
        favorites = self.obj1.get_favorites()
        self.assertIn(genre, favorites)
        self.assertQuerysetEqual(favorites[genre], expected[genre])
        self.assertIn(schlagwort, favorites)
        self.assertQuerysetEqual(favorites[schlagwort], expected[schlagwort])

        # If an invalid model is provided, return an empty Favoriten queryset
        expected = self.model.objects.none()
        self.assertQuerysetEqual(self.obj1.get_favorites(_models.artikel), expected)

        expected = self.obj1.fav_genres.all()
        self.assertQuerysetEqual(self.obj1.get_favorites(genre), expected)

        expected = self.obj1.fav_schl.all()
        self.assertQuerysetEqual(self.obj1.get_favorites(schlagwort), expected)

    def test_get_favorite_models(self):
        expected = [_models.genre, _models.schlagwort]
        self.assertEqual(self.model.get_favorite_models(), expected)
