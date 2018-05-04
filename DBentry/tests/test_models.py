from .base import *

class TestModelBase(DataTestCase):

    model = artikel
    add_relations = True
    test_data_count = 1        

    def test_qs(self):
        from django.db import models
        self.assertIsInstance(self.obj1.qs(), models.QuerySet)
        self.assertEqual(self.obj1.qs().count(), 1)
        self.assertListEqualSorted(self.obj1.qs(), self.queryset.filter(pk=self.obj1.pk))

    def test_qs_exception(self):
        with self.assertRaises(AttributeError):
            self.model.qs(self.model)

    def test_get_basefields(self):
        self.assertListEqualSorted(
            self.model.get_basefields(True), ['schlagzeile', 'seite', 'seitenumfang', 'zusammenfassung']
        )

    def test_get_foreignfields(self):
        self.assertListEqualSorted(self.model.get_foreignfields(True), ['ausgabe'])

    def test_get_m2mfields(self):
        expected = [
            'm2m_artikel_autor', 'm2m_artikel_band', 'm2m_artikel_genre', 'm2m_artikel_musiker', 'm2m_artikel_ort', 
            'm2m_artikel_person', 'm2m_artikel_schlagwort', 'm2m_artikel_spielort', 'm2m_artikel_veranstaltung', 'genre', 
            'schlagwort', 'person', 'autor', 'band', 'musiker', 'ort', 'spielort', 'veranstaltung'
        ]
        self.assertListEqualSorted(self.model.get_m2mfields(True), expected)

    def test_get_required_fields(self):
        self.assertListEqualSorted(self.model.get_required_fields(True), ['ausgabe', 'schlagzeile', 'seite'])

    def test_get_search_fields(self):
        expected = ['schlagzeile', 'zusammenfassung', 'beschreibung']
        self.assertListEqualSorted(self.model.get_search_fields(True), expected)

    def test_get_updateable_fields(self):
        # The DataFactory provided an instance with only the required fields filled out
        self.assertEqual(self.obj1.get_updateable_fields(), ['seitenumfang', 'zusammenfassung', 'beschreibung', 'bemerkungen'])

        self.obj1.seitenumfang = 'f'
        self.obj1.beschreibung = 'Beep'
        self.assertListEqualSorted(self.obj1.get_updateable_fields(), ['bemerkungen', 'zusammenfassung'])
        self.obj1.zusammenfassung = 'Boop'
        self.assertListEqualSorted(self.obj1.get_updateable_fields(), ['bemerkungen'])

    def test_get_updateable_fields_not_ignores_default(self):
        # get_updateable_fields should include fields that have their default value
        # artikel has no 'useful' defaults to test with
        obj = person(vorname='Alice') # nachname has default 
        obj.save()
        self.assertListEqualSorted(obj.get_updateable_fields(), ['beschreibung','nachname', 'bemerkungen'])

@tag("cn")    
class TestComputedNameModel(DataTestCase):

    model = ausgabe
    default = ausgabe._name_default % {'verbose_name':ausgabe._meta.verbose_name}

    @classmethod
    def setUpTestData(cls):
        cls.mag = DataFactory().create_obj(magazin)
        monat.objects.create(id=12, monat='Dezember', abk ='Dez')
        cls.obj1 = ausgabe(magazin=cls.mag)
        cls.obj1.save()

        cls.obj2 = ausgabe(magazin=cls.mag)
        cls.obj2.save()

        cls.test_data = [cls.obj1, cls.obj2]

        super().setUpTestData()

    def test_init(self):
        # The name should be updated upon init
        self.qs_obj1.update(_changed_flag=True, beschreibung='Testinfo', sonderausgabe=True)
        obj = self.qs_obj1.first()
        self.assertFalse(obj._changed_flag)
        self.assertEqual(obj._name,  "Testinfo")

    def test_get_basefields(self):
        # _name and _changed_flag should not appear in get_basefields
        self.assertNotIn('_name', self.model.get_basefields(True))
        self.assertNotIn('_changed_flag', self.model.get_basefields(True))

    def test_get_search_fields(self):
        # _name should be used in searches, that's the whole point of this endeavour
        self.assertIn('_name', self.model.get_search_fields())
        self.assertNotIn('_changed_flag', self.model.get_search_fields())

        # _name should always be the first field in search_fields
        self.model.search_fields += ['_name']
        self.assertEqual(self.model.get_search_fields()[0], '_name')

    def test_get_updateable_fields(self):
        # _name and _changed_flag should not appear in get_updateable_fields even if empty/default value
        obj = ausgabe(magazin=self.mag)
        self.assertFalse('_name' in obj.get_updateable_fields())
        self.assertFalse('_changed_flag' in obj.get_updateable_fields())

    def test_name_default(self):
        self.assertEqual(str(self.obj1), self.default)

    def test_update_name_notexplodes_on_no_pk_and_forced(self):
        # Unsaved instances should be ignored, as update_name relies on filtering queries with the instance's pk.
        obj = ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name(force_update = True))

    def test_update_name_aborts_on_no_pk(self):
        # Unsaved instances should be ignored, as update_name relies on filtering queries with the instance's pk.
        obj = ausgabe(magazin=self.mag)
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

    model = artikel

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = DataFactory().create_obj(artikel)
        cls.test_data = [cls.obj1]

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), str(self.obj1.schlagzeile))
        self.qs_obj1.update(schlagzeile='')
        self.assertEqual(self.qs_obj1.first().__str__(), 'Keine Schlagzeile gegeben!')
        self.qs_obj1.update(zusammenfassung='Dies ist eine Testzusammenfassung, die nicht besonders lang ist.')
        self.assertEqual(self.qs_obj1.first().__str__(), 'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.')

    def test_zusammenfassung_string(self):
        self.assertEqual(self.qs_obj1.first().zusammenfassung_string(), '')
        self.qs_obj1.update(zusammenfassung='Dies ist eine Testzusammenfassung, die nicht besonders lang ist.')
        self.assertEqual(self.qs_obj1.first().zusammenfassung_string(), 'Dies ist eine Testzusammenfassung, die nicht [...]')

    def test_artikel_magazin(self):
        m = magazin.objects.create(magazin_name='Testmagazin')
        self.obj1.ausgabe.magazin = m
        self.assertEqual(self.obj1.artikel_magazin(), m)

    def test_schlagwort_string(self):
        s1 = schlagwort.objects.create(schlagwort = 'Testschlagwort1')
        self.model.schlagwort.through.objects.create(schlagwort = s1, artikel = self.obj1)
        s2 = schlagwort.objects.create(schlagwort = 'Testschlagwort2')
        self.model.schlagwort.through.objects.create(schlagwort = s2, artikel = self.obj1)
        self.assertEqual(self.qs_obj1.first().schlagwort_string(), 'Testschlagwort1, Testschlagwort2')

    def test_kuenstler_string(self):
        m = musiker.objects.create(kuenstler_name='Alice Tester')
        self.model.musiker.through.objects.create(musiker=m, artikel=self.obj1)
        b = band.objects.create(band_name='Testband')
        self.model.band.through.objects.create(band=b, artikel=self.obj1)
        self.assertEqual(self.qs_obj1.first().kuenstler_string(), 'Testband, Alice Tester')

class TestModelAudio(DataTestCase):

    model = audio

    @classmethod
    def setUpTestData(cls):
        cls.obj1 = audio.objects.create(titel='Testaudio')
        cls.test_data = [cls.obj1]

        super().setUpTestData()

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testaudio')

    def test_save(self):
        self.obj1.save()
        self.assertEqual(self.obj1.discogs_url, None)
        self.obj1.release_id = 1
        self.obj1.save()
        self.assertEqual(self.obj1.discogs_url, "http://www.discogs.com/release/1")

    def test_kuenstler_string(self):
        m = musiker.objects.create(kuenstler_name='Alice Tester')
        self.model.musiker.through.objects.create(musiker=m, audio=self.obj1)
        b = band.objects.create(band_name='Testband')
        self.model.band.through.objects.create(band=b, audio=self.obj1)
        self.assertEqual(self.qs_obj1.first().kuenstler_string(), 'Testband, Alice Tester')

    def test_formate_string(self):
        ft = FormatTyp.objects.create(typ='TestTyp1')
        Format.objects.create(format_name='Testformat1', format_typ=ft, audio=self.obj1)
        ft = FormatTyp.objects.create(typ='TestTyp2')
        Format.objects.create(format_name='Testformat2', format_typ=ft, audio=self.obj1)
        # format_name is a non-editable field (compiled of the Format's properties), its use is mainly for autocomplete searches
        # any format_name set manually should be overriden by Format.get_name()
        self.assertEqual(self.qs_obj1.first().formate_string(), 'TestTyp1, TestTyp2')
        
class TestModelAusgabe(DataTestCase):

    model = ausgabe

    @translation_override(language = None)
    def test_get_name(self):
        # 1. sonderausgabe + beschreibung
        # 2. !jahre + jahrgang/!jahrgang
        # 3. ausgaben_merkmal>e_datum>monat>lnum>?
        # 4. num>monat>lnum>e_datum>beschreibung>k.A.

        # sonderausgabe + beschreibung => beschreibung
        name_data = {'sonderausgabe':True, 'beschreibung':'Test-Info'}
        expected = 'Test-Info'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'sonderausgabe + beschreibung => beschreibung')
        # sonderausgabe + beschreibung + any other data => beschreibung
        name_data.update({'jahrgang':'2','ausgabe_jahr__jahr':['2020'], 'ausgabe_monat__monat__abk':['Dez']})
        expected = 'Test-Info'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'sonderausgabe + beschreibung + any other data => beschreibung')

        # with jahr:
        # monat
        name_data = {'ausgabe_jahr__jahr':['2020'], 'ausgabe_monat__monat__abk':['Dez']}
        expected = "2020-Dez"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahr: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahr: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21 (2020)"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "2020-20"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahr: monat + e_datum + lnum + num => num')

        # with jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Dez'], 'jahrgang':'2'}
        expected = "Jg. 2-Dez"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahrgang: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21 (Jg. 2)"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "Jg. 2-20"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahrgang: monat + e_datum + lnum + num => num')

        # without jahr or jahrgang:
        # monat
        name_data = {'ausgabe_monat__monat__abk':['Dez']}
        expected = "k.A.-Dez"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat => monat')

        # monat + e_datum => e_datum
        name_data.update({'e_datum':'02.05.2018'})
        expected = '02.05.2018'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum => e_datum')

        # monat + e_datum + lnum => lnum
        name_data.update({'ausgabe_lnum__lnum':['21']})
        expected = "21"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum => lnum')

        # monat + e_datum + lnum + num => num
        name_data.update({'ausgabe_num__num':['20']})
        expected = "k.A.-20"
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'no jahr/jahrgang: monat + e_datum + lnum + num => num')

        # only beschreibung
        name_data = {'beschreibung':'Test-Info'}
        expected = 'Test-Info'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = ' only beschreibung')

        # no data whatsoever
        name_data = {}
        expected = 'No data for Ausgabe.'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'jahrgang: monat => monat')

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
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'merkmal: e_datum')

        name_data.update({'magazin__ausgaben_merkmal':'monat'})
        expected = '2020-Dez'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'merkmal: monat')

        name_data.update({'magazin__ausgaben_merkmal':'num'})
        expected = '2020-20'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'merkmal: num')

        name_data.update({'magazin__ausgaben_merkmal':'lnum'})
        expected = '21 (2020)'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'merkmal: lnum')

        name_data.update({'ausgabe_jahr__jahr':[]})
        expected = '21'
        self.assertEqual(ausgabe._get_name(**name_data), expected, msg = 'merkmal: lnum + no jahr')

        # merkmal set but the ausgabe contains no data for it
        name_data = {'magazin__ausgaben_merkmal':'num', 'beschreibung' : 'Woops!'}
        expected = 'Woops!'
        self.assertEqual(ausgabe._get_name(**name_data), expected)
        
class TestModelAusgabeJahr(DataTestCase):
    
    model = ausgabe_jahr
    
    def test_str(self):
        ausgabe_object = ausgabe.objects.create(magazin = magazin.objects.create(magazin_name='Testmagazin'))
        obj = self.model(jahr='2018', ausgabe=ausgabe_object)
        self.assertEqual(str(obj), '2018')
        
class TestModelAusgabeLnum(DataTestCase):
    
    model = ausgabe_lnum
    
    def test_str(self):
        ausgabe_object = ausgabe.objects.create(magazin = magazin.objects.create(magazin_name='Testmagazin'))
        obj = self.model(lnum='21', ausgabe=ausgabe_object)
        self.assertEqual(str(obj), '21')
        
class TestModelAusgabeMonat(DataTestCase):
    
    model = ausgabe_monat
    
    def test_str(self):
        ausgabe_object = ausgabe.objects.create(magazin = magazin.objects.create(magazin_name='Testmagazin'))
        monat_object = monat.objects.create(monat='Dezember', abk='Dez')
        obj = self.model(monat=monat_object, ausgabe=ausgabe_object)
        self.assertEqual(str(obj), 'Dez')
        
class TestModelAusgabeNum(DataTestCase):
    
    model = ausgabe_num
    
    def test_str(self):
        ausgabe_object = ausgabe.objects.create(magazin = magazin.objects.create(magazin_name='Testmagazin'))
        obj = self.model(num='20', ausgabe=ausgabe_object)
        self.assertEqual(str(obj), '20')

class TestModelAutor(DataTestCase):

    model = autor

    @translation_override(language = None)
    def test_get_name(self):
        # 1. person_name + kuerzel
        # 2. person_name
        # 3. kuerzel
        # 4. cls._name_default
        name_data = {'person___name':'Alice Tester', 'kuerzel':'TK'}
        expected = 'Alice Tester (TK)'
        self.assertEqual(autor._get_name(**name_data), expected)

        name_data = {'person___name':'Alice Tester'}
        expected = 'Alice Tester'
        self.assertEqual(autor._get_name(**name_data), expected)

        name_data = {'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(autor._get_name(**name_data), expected)

        name_data = {}
        expected = 'No data for Autor.'
        self.assertEqual(autor._get_name(**name_data), expected)

        # get_name should ignore default values for person
        name_data = {'person___name':'No data for Person.', 'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(autor._get_name(**name_data), expected)

        name_data = {'person___name':'unbekannt', 'kuerzel':'TK'}
        expected = 'TK'
        self.assertEqual(autor._get_name(**name_data), expected)

class TestModelBand(DataTestCase):

    model = band
    
    def test_str(self):
        obj = self.model(band_name='Testband', beschreibung = 'Beep', bemerkungen = 'Boop')
        self.assertEqual(str(obj), 'Testband')
        
class TestModelBestand(DataTestCase):
    pass
    
class TestModelBildmaterial(DataTestCase):
    pass

class TestModelBuch(DataTestCase):
    pass
    
class TestModelBuchSerie(DataTestCase):
    pass
        
class TestModelBundesland(DataTestCase):
    
    model = bundesland
    
    def test_str(self):
        land_object = land.objects.create(land_name = 'Deutschland', code='DE')
        obj = self.model(bland_name ='Hessen', code = 'DE-HE', land = land_object)
        self.assertEqual(str(obj), 'Hessen DE-HE')

class TestModelDatei(DataTestCase):

    model = datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')
        
class TestModelDokument(DataTestCase):
    pass

class TestModelFormat(DataTestCase):
    
    model = Format
    
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
    
    model = FormatSize
    
    def test_str(self):
        obj = self.model(size='LP')
        self.assertEqual(str(obj), 'LP')

class TestModelFormatTag(DataTestCase):

    model = FormatTag

    def test_str(self):
        obj = self.model(tag='Testtag')
        self.assertEqual(str(obj), 'Testtag')
        
class TestModelFormatTyp(DataTestCase):
    
    model = FormatTyp
    
    def test_str(self):
        obj = FormatTyp(typ='Test')
        self.assertEqual(str(obj), 'Test')
        
class TestModelGeber(DataTestCase):
    
    model = geber
    
    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

class TestModelGenre(DataTestCase):

    model = genre
    
    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')
        
class TestModelInstrument(DataTestCase):

    model = instrument

    def test_str(self):
        obj = self.model(instrument = 'Posaune', kuerzel = 'pos')
        self.assertEqual(str(obj), 'Posaune (pos)')
        
        obj = self.model(instrument = 'Posaune', kuerzel = '')
        self.assertEqual(str(obj), 'Posaune')
        
class TestModelKreis(DataTestCase):
    pass

class TestModelLagerort(DataTestCase):

    model = lagerort

    def test_get_name(self):        
        # ort only
        name_data = {'ort':'Testort'}
        expected = 'Testort'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort only')
        
        # ort + regal
        name_data.update({'regal':'Testregal'})
        expected = 'Testregal (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + regal')
        
        # ort + raum
        name_data = {'ort':'Testort', 'raum':'Testraum'}
        expected = 'Testraum (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + raum')
        
        # ort + raum + regal
        name_data.update({'regal':'Testregal'})
        expected = 'Testraum-Testregal (Testort)'
        self.assertEqual(self.model._get_name(**name_data), expected, msg = 'ort + raum + regal')
        
class TestModelLand(DataTestCase):
    
    model = land
    
    def test_str(self):
        obj = self.model(land_name = 'Deutschland', code='DE')
        self.assertEqual(str(obj), 'Deutschland DE')

class TestModelMagazin(DataTestCase):

    model = magazin
    
    def test_str(self):
        obj = self.model(magazin_name='Testmagazin')
        self.assertEqual(str(obj), 'Testmagazin')
        
class TestModelMemorabilien(DataTestCase):
    pass
        
class TestModelMonat(DataTestCase):
    
    model = monat
    
    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

class TestModelMusiker(DataTestCase):

    model = musiker

    def test_str(self):
        obj = self.model(kuenstler_name='Alice Tester', beschreibung = 'Beep', bemerkungen = 'Boop')
        self.assertEqual(str(obj), 'Alice Tester')
        
class TestModelNoiseRed(DataTestCase):
    
    model = NoiseRed
    
    def test_str(self):
        obj = self.model(verfahren='Beepboop')
        self.assertEqual(str(obj), 'Beepboop')
        
class TestModelOrt(DataTestCase):

    model = ort
        
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
        
class TestModelPerson(DataTestCase):

    model = person

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
    
    model = plattenfirma
    
    def test_str(self):
        obj = plattenfirma(name='Testfirma')
        self.assertEqual(str(obj), 'Testfirma')
        
class TestModelProvenienz(DataTestCase):

    model = provenienz

    def test_str(self):
        obj = provenienz(geber=geber.objects.create(name='TestGeber'), typ='Fund')
        self.assertEqual(str(obj), 'TestGeber (Fund)')
        
class TestModelSchlagwort(DataTestCase):

    model = schlagwort
    
    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')
        
class TestModelSender(DataTestCase):
    
    model = sender
    
    def test_str(self):
        obj = self.model(name = 'Testsender')
        self.assertEqual(str(obj), 'Testsender')
        
class TestModelSpielort(DataTestCase):
    
    model = spielort
    
    def test_str(self):
        land_object = land.objects.create(land_name = 'Deutschland', code='DE')
        obj = self.model(name = 'Testspielort', ort = ort.objects.create(land=land_object))
        self.assertEqual(str(obj), 'Testspielort')
        
class TestModelSprache(DataTestCase):
    
    model = sprache
    
    def test_str(self):
        obj = self.model(sprache = 'Deutsch', abk = 'de')
        self.assertEqual(str(obj), 'Deutsch de')
        
class TestModelTechnik(DataTestCase):
    pass
        
class TestModelVeranstaltung(DataTestCase):
    
    model = veranstaltung
    
    def test_str(self):
        land_object = land.objects.create(land_name = 'Deutschland', code='DE')
        spielort_object = spielort(name = 'Testspielort', ort = ort.objects.create(land=land_object))
        obj = self.model(name='Testveranstaltung', datum = '02.05.2018', spielort = spielort_object)
        self.assertEqual(str(obj), 'Testveranstaltung (02.05.2018)')
        
class TestModelVerlag(DataTestCase):
    
    model = verlag
    
    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')
        
class TestModelVideo(DataTestCase):
    pass
    

class TestModelFavoriten(DataTestCase, UserTestCase):

    model = Favoriten

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData() # create the users
        cls.obj1 = Favoriten.objects.create(user=cls.super_user)
        cls.obj1.fav_genres.add(genre.objects.create(genre='Testgenre1'))
        cls.obj1.fav_genres.add(genre.objects.create(genre='Testgenre2'))
        cls.obj1.fav_schl.add(schlagwort.objects.create(schlagwort='Testwort1'))
        cls.obj1.fav_schl.add(schlagwort.objects.create(schlagwort='Testwort2'))

        cls.test_data = [cls.obj1]

    def test_str(self):
        self.assertEqual(str(self.obj1), 'Favoriten von superuser')

    def test_get_favorites(self):
        # If no model is provided, return all favorites as a dict 
        expected = {genre : self.obj1.fav_genres.all(), schlagwort : self.obj1.fav_schl.all()}
        favorites = self.obj1.get_favorites()
        self.assertIn(genre, favorites)
        self.assertQuerysetEqual(favorites[genre], expected[genre])
        self.assertIn(schlagwort, favorites)
        self.assertQuerysetEqual(favorites[schlagwort], expected[schlagwort])

        # If an invalid model is provided, return an empty Favoriten queryset
        expected = Favoriten.objects.none()
        self.assertQuerysetEqual(self.obj1.get_favorites(artikel), expected)

        expected = self.obj1.fav_genres.all()
        self.assertQuerysetEqual(self.obj1.get_favorites(genre), expected)

        expected = self.obj1.fav_schl.all()
        self.assertQuerysetEqual(self.obj1.get_favorites(schlagwort), expected)

    def test_get_favorite_models(self):
        expected = [genre, schlagwort]
        self.assertEqual(Favoriten.get_favorite_models(), expected)
        
class TestGetModelFields(TestCase):
    pass
    
class TestGetModelRelations(TestCase):
    pass
