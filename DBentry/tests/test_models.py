from .base import *

class TestModelsBase(TestCase):
    
    model = None
    test_data = []
    
    def setUp(self):
        for c, obj in enumerate(self.test_data, 1):
            obj.refresh_from_db()
            if self.model:
                setattr(self, 'qs_obj' + str(c), self.model.objects.filter(pk=obj.pk))
        
class TestModelAusgabe(TestModelsBase):
    
    model = ausgabe
   
    @classmethod
    def setUpTestData(cls):
        cls.mag = DataFactory().create_obj(magazin)
        monat.objects.create(id=12, monat='Dezember', abk ='Dez')
        cls.obj1 = ausgabe(magazin=cls.mag)
        cls.obj1.save()
        
        cls.obj2 = ausgabe(magazin=cls.mag)
        cls.obj2.save()
        
        cls.test_data = [cls.obj1, cls.obj2]
        
    def test_anz_artikel(self):
        self.assertEqual(self.obj1.anz_artikel(), 0)
        d = {'schlagzeile' : 'Beep', 'seite' : 1, 'ausgabe' : self.obj1}
        artikel.objects.create(**d)
        self.assertEqual(self.obj1.anz_artikel(), 1)
        
    def test_X_strings(self):
        obj = ausgabe.objects.get(pk=self.obj1.pk)
        obj.ausgabe_jahr_set.create(jahr=2020)
        obj.ausgabe_jahr_set.create(jahr=2021)
        obj.ausgabe_jahr_set.create(jahr=2022)
        self.assertEqual(obj.jahre(), '2020, 2021, 2022')
        
        obj.ausgabe_num_set.create(num=10)
        obj.ausgabe_num_set.create(num=11)
        obj.ausgabe_num_set.create(num=12)
        self.assertEqual(obj.num_string(), '10, 11, 12')
        
        obj.ausgabe_lnum_set.create(lnum=10)
        obj.ausgabe_lnum_set.create(lnum=11)
        obj.ausgabe_lnum_set.create(lnum=12)
        self.assertEqual(obj.lnum_string(), '10, 11, 12')
        
        obj.ausgabe_monat_set.create(monat=monat.objects.create(id=1, monat='Januar', abk='Jan'))
        obj.ausgabe_monat_set.create(monat=monat.objects.create(id=2, monat='Februar', abk='Feb'))
        self.assertEqual(obj.monat_string(), 'Jan, Feb')
        
    def test_str(self):
        # 1. sonderausgabe + info
        # 2. !jahre + jahrgang/!jahrgang
        # 3. ausgaben_merkmal>e_datum>monat>lnum>?
        # 4. num>monat>lnum>e_datum>info>k.A.
        
        obj1_qs = ausgabe.objects.filter(pk=self.obj1.pk)
        self.assertEqual(obj1_qs.first().__str__(), "Keine Angaben zu dieser Ausgabe!")
        obj1_qs.update(info = 'Test-Info')
        self.assertEqual(obj1_qs.first().__str__(), 'Test-Info') # only info
        obj1_qs.update(sonderausgabe = True)
        self.assertEqual(obj1_qs.first().__str__(), 'Test-Info') # sonderausgabe + info
        obj1_qs.update(jahrgang = '2')
        self.assertEqual(obj1_qs.first().__str__(), 'Test-Info') # str should still prioritize info 
        
        obj1_qs.update(sonderausgabe = False)
        # Test if jahrgang is used properly in place of jahre
        obj1_qs.first().ausgabe_lnum_set.create(lnum=21)
        self.assertEqual(obj1_qs.first().__str__(), "21 (Jg.2)")
        
        obj1_qs.first().ausgabe_monat_set.create(monat=monat.objects.get(monat='Dezember'))
        self.assertEqual(obj1_qs.first().__str__(), "Jg.2-Dez")
        
        obj1_qs.first().ausgabe_num_set.create(num=20)
        self.assertEqual(obj1_qs.first().__str__(), "Jg.2-20")
        
        # Tests with jahre and jahrgang
        obj1_qs.first().ausgabe_jahr_set.create(jahr=2020)
        self.assertEqual(obj1_qs.first().__str__(), "2020-20") # expected num
        
        obj1_qs.first().ausgabe_num_set.all().delete()
        self.assertEqual(obj1_qs.first().__str__(), "2020-Dez") # expected monat
        
        obj1_qs.first().ausgabe_monat_set.all().delete()
        self.assertEqual(obj1_qs.first().__str__(), "21 (2020)") # expected lnum 
        
        obj1_qs.update(jahrgang=None)
        obj1_qs.first().ausgabe_jahr_set.all().delete()
        self.assertEqual(obj1_qs.first().__str__(), "21") # expected lnum with jahre = k.A.
        
        
        # Tests with ausgaben_merkmal override set
        obj2_qs = ausgabe.objects.filter(pk=self.obj2.pk)
        obj2_qs.update(e_datum = '2098-12-10')
        self.assertEqual(obj2_qs.first().__str__(), '2098-12-10') # e_datum only, no call to save() thus no year or month
        
        self.obj2.magazin.ausgaben_merkmal = 'e_datum'
        self.obj2.magazin.save()
        self.assertEqual(obj2_qs.first().__str__(), '2098-12-10') # merkmal + e_datum
        
        self.obj2.magazin.ausgaben_merkmal = 'num'
        self.obj2.magazin.save()
        obj2_qs.first().ausgabe_jahr_set.create(jahr=2098)
        obj2_qs.first().ausgabe_num_set.create(num=20)
        self.assertEqual(obj2_qs.first().__str__(), "2098-20") # merkmal + e_datum + num => num
        
        self.obj2.magazin.ausgaben_merkmal = 'lnum'
        self.obj2.magazin.save()
        obj2_qs.first().ausgabe_lnum_set.create(lnum=21)
        self.assertEqual(obj2_qs.first().__str__(), "21 (2098)") # merkmal + e_datum + num + lnum => lnum
        obj2_qs.first().ausgabe_jahr_set.all().delete()
        self.assertEqual(obj2_qs.first().__str__(), "21") # merkmal + e_datum + num + lnum => lnum with jahre = k.A.
        
        self.obj2.magazin.ausgaben_merkmal = 'monat'
        self.obj2.magazin.save()
        obj2_qs.first().ausgabe_jahr_set.create(jahr=2098)
        obj2_qs.first().ausgabe_monat_set.create(monat=monat.objects.get(monat='Dezember'))
        self.assertEqual(obj2_qs.first().__str__(), "2098-Dez") # merkmal + e_datum + num + lnum + monat => monat
                
        self.obj2.magazin.ausgaben_merkmal = ''
        self.obj2.magazin.save()
        self.assertEqual(obj2_qs.first().__str__(), "2098-20") # check whether the ausgaben_merkmal override is now inactive
    
    # Manipulating in-memory instances, do this test last
    def test_z_save(self):
        self.obj1.e_datum = '2098-12-10'
        self.obj1.save()
        self.assertQuerysetEqual(self.obj1.ausgabe_jahr_set.values_list('jahr', flat = True), ['2098'], ordered = False)
        self.assertQuerysetEqual(self.obj1.ausgabe_monat_set.values_list('monat__abk', flat = True), ['Dez'], ordered = False, transform = str)
        
        # Check if save() adds a new year/month given through e_datum
        self.obj2.ausgabe_jahr_set.create(jahr=2020)
        self.obj2.ausgabe_monat_set.create(monat=monat.objects.create(monat='November', abk='Nov'))
        self.obj2.e_datum = '2021-12-10'
        self.obj2.save()
        self.assertQuerysetEqual(self.obj2.ausgabe_jahr_set.values_list('jahr', flat = True), ['2020', '2021'], ordered = False)
        self.assertQuerysetEqual(self.obj2.ausgabe_monat_set.values_list('monat__abk', flat = True), ['Dez', 'Nov'], ordered = False, transform = str)

class TestModelPerson(TestModelsBase):
    
    model = person
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = person(vorname='Alice', nachname='Tester')
        cls.obj1.save()
        cls.test_data = [cls.obj1]
        
    def test_autoren_string(self):
        autor.objects.create(kuerzel='Testautor1', person=self.obj1)
        autor.objects.create(kuerzel='Testautor2', person=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().autoren_string(), 'Alice Tester (Testautor1), [...]') # autor.str() => '{str(person)} ({kuerzel})
        
    def test_musiker_string(self):
        musiker.objects.create(kuenstler_name='Testkuenstler1', person=self.obj1)
        musiker.objects.create(kuenstler_name='Testkuenstler2', person=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().musiker_string(), 'Testkuenstler1, Testkuenstler2')
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Alice Tester')
        
class TestModelMusiker(TestModelsBase):
    
    model = musiker
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = musiker.objects.create(kuenstler_name='Alice Tester')
        cls.test_data = [cls.obj1]
        
    def test_band_string(self):
        b1 = band.objects.create(band_name='Testband1')
        musiker.band_set.through.objects.create(band=b1, musiker=self.obj1)
        b2 = band.objects.create(band_name='Testband2')
        musiker.band_set.through.objects.create(band=b2, musiker=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().band_string(), 'Testband1, Testband2')
        
    def test_genre_string(self):
        g1 = genre.objects.create(genre='Testgenre1')
        self.model.genre.through.objects.create(genre=g1, musiker=self.obj1)
        g2 = genre.objects.create(genre='Testgenre2')
        self.model.genre.through.objects.create(genre=g2, musiker=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().genre_string(), 'Testgenre1, Testgenre2')
        
    def test_herkunft_string(self):
        self.assertEqual(self.obj1.herkunft_string(), '---')
        o = ort.objects.create(stadt='Dortmund', land=land.objects.create(land_name='Testland', code='TE'))
        p = person.objects.create(vorname='Alice', nachname='Tester', herkunft=o)
        self.qs_obj1.update(person=p)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().herkunft_string(), 'Dortmund, TE')
        
class TestModelGenre(TestModelsBase):
    
    model = genre
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = genre.objects.create(genre='Testgenre')
        cls.test_data = [cls.obj1]
        
    def test_alias_string(self):
        genre_alias.objects.create(alias='Alias1', parent=self.obj1)
        genre_alias.objects.create(alias='Alias2', parent=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().alias_string(), 'Alias1, Alias2')
        
class TestModelSchlagwort(TestModelsBase):
    
    model = schlagwort
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = schlagwort.objects.create(schlagwort='Testschlagwort')
        cls.test_data = [cls.obj1]
        
    def test_num_artikel(self):
        self.assertEqual(self.obj1.num_artikel(), 0)
        self.model.artikel_set.through.objects.create(artikel=DataFactory().create_obj(artikel), schlagwort = self.obj1)
        self.assertEqual(self.obj1.num_artikel(), 1)
        
    def test_alias_string(self):
        schlagwort_alias.objects.create(alias='Alias1', parent=self.obj1)
        schlagwort_alias.objects.create(alias='Alias2', parent=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().alias_string(), 'Alias1, Alias2')
        
class TestModelBand(TestModelsBase):
    
    model = band
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = band.objects.create(band_name='Testband')
        cls.test_data = [cls.obj1]
        
    def test_alias_string(self):
        band_alias.objects.create(alias='Alias1', parent=self.obj1)
        band_alias.objects.create(alias='Alias2', parent=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().alias_string(), 'Alias1, Alias2')
        
    def test_genre_string(self):
        g1 = genre.objects.create(genre='Testgenre1')
        self.model.genre.through.objects.create(genre=g1, band=self.obj1)
        g2 = genre.objects.create(genre='Testgenre2')
        self.model.genre.through.objects.create(genre=g2, band=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().genre_string(), 'Testgenre1, Testgenre2')
        
    def test_musiker_string(self):
        m1 = musiker.objects.create(kuenstler_name='Testkuenstler1')
        self.model.musiker.through.objects.create(musiker=m1, band=self.obj1)
        m2 = musiker.objects.create(kuenstler_name='Testkuenstler2')
        self.model.musiker.through.objects.create(musiker=m2, band=self.obj1)
        self.assertEqual(self.model.objects.filter(pk=self.obj1.pk).first().musiker_string(), 'Testkuenstler1, Testkuenstler2')
        
class TestModelAutor(TestModelsBase):
    
    model = autor
    
    @classmethod
    def setUpTestData(cls):
        p = person.objects.create(vorname='Alice', nachname='Tester')
        cls.obj1 = autor.objects.create(person=p)
        cls.test_data = [cls.obj1]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Alice Tester') #NOTE: or test for self.obj1.person.__str__()?
        self.model.objects.filter(pk=self.obj1.pk).update(kuerzel='TK')
        self.assertEqual(self.qs_obj1.first().__str__(), 'Alice Tester (TK)')
        
    def test_magazin_string(self):
        self.model.magazin.through.objects.create(magazin=magazin.objects.create(magazin_name='Testmagazin1'), autor=self.obj1)
        self.model.magazin.through.objects.create(magazin=magazin.objects.create(magazin_name='Testmagazin2'), autor=self.obj1)
        self.assertEqual(self.qs_obj1.first().magazin_string(), 'Testmagazin1, Testmagazin2')
        
class TestModelArtikel(TestModelsBase):
    
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
        
class TestModelInstrument(TestModelsBase):
    
    model = instrument
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = instrument.objects.create(instrument = 'Posaune', kuerzel = 'pos')
        cls.test_data = [cls.obj1]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Posaune (pos)')
        self.qs_obj1.update(kuerzel='')
        self.assertEqual(self.qs_obj1.first().__str__(), 'Posaune')
        
class TestModelMagazin(TestModelsBase):
    
    model = magazin
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = magazin.objects.create(magazin_name='Testmagazin')
        cls.test_data = [cls.obj1]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testmagazin')
        
    def test_anz_ausgaben(self):
        self.assertEqual(self.obj1.anz_ausgaben(), 0)
        ausgabe.objects.create(magazin=self.obj1)
        self.assertEqual(self.qs_obj1.first().anz_ausgaben(), 1)
        
class TestModelAudio(TestModelsBase):
    
    model = audio
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = audio.objects.create(titel='Testaudio')
        cls.test_data = [cls.obj1]
        
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
        
class TestModelProvenienz(TestModelsBase):
    
    model = provenienz
    
    @classmethod
    def setUpTestData(cls):
        g = geber.objects.create(name='TestGeber')
        cls.obj1 = provenienz.objects.create(geber=g, typ='Fund')
        cls.test_data = [cls.obj1]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'TestGeber (Fund)')
        
class TestModelLagerort(TestModelsBase):
    
    model = lagerort
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = lagerort.objects.create(ort = 'Testort', signatur = '001')
        cls.obj2 = lagerort.objects.create(ort = 'Testort')
        cls.obj3 = lagerort.objects.create(ort = 'Testort', raum='Testraum')
        cls.obj4 = lagerort.objects.create(ort = 'Testort', regal='Testregal')
        cls.obj5 = lagerort.objects.create(ort = 'Testort', raum='Testraum', regal='Testregal')
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4, cls.obj5]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), '001')
        self.assertEqual(self.obj2.__str__(), 'Testort')
        self.assertEqual(self.obj3.__str__(), 'Testraum (Testort)')
        self.assertEqual(self.obj4.__str__(), 'Testregal (Testort)')
        self.assertEqual(self.obj5.__str__(), 'Testraum-Testregal (Testort)')
        
class TestModelFormat(TestModelsBase):
    
    model = Format
    
    @classmethod
    def setUpTestData(cls):
        a = DataFactory().create_obj(audio)
        ft = FormatTyp.objects.create(typ='TestTyp')
        fs = FormatSize.objects.create(size='LP')
        t = FormatTag.objects.create(tag='Compilation')
        cls.obj1 = Format.objects.create(format_name='Testformat1', format_typ=ft, audio=a)
        cls.obj2 = Format.objects.create(format_typ=ft, audio=a)
        cls.obj3 = Format.objects.create(format_typ=ft, audio=a, format_size=fs)
        cls.obj4 = Format.objects.create(format_typ=ft, audio=a, format_size=fs, anzahl=2, channel='Stereo')
        cls.obj4.tag.add(t) #NOTE: this doesn't update obj4.format_name!!
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        
        # Create an unsaved, prepared instance for the save test
        cls.obj5 = Format(format_typ=ft, audio=a, format_size=fs)
        
    def test_get_name(self):
        self.assertEqual(self.obj2.get_name(), 'TestTyp')
        self.assertEqual(self.obj3.get_name(), 'LP')
        self.assertEqual(self.obj4.get_name(), '2xLP, Compilation, Stereo')
        
    def test_str(self):
        # format_name is a non-editable field (compiled of the Format's properties), its use is mainly for autocomplete searches
        # any format_name set manually should be overriden by Format.get_name()
        self.assertEqual(self.obj1.__str__(), 'TestTyp')
        self.assertEqual(self.obj2.__str__(), 'TestTyp')
        self.assertEqual(self.obj3.__str__(), 'LP')
        self.assertEqual(self.obj4.__str__(), '2xLP, Compilation, Stereo')
        
    def test_save(self):
        self.assertEqual(self.obj5.format_name, '')
        self.obj5.save()
        self.assertEqual(self.obj5.format_name, self.obj5.get_name())
        
class TestModelFormatTag(TestModelsBase):
    
    model = FormatTag
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = FormatTag.objects.create(tag='Test')
        cls.test_data = [cls.obj1]
    
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Test')
    
class TestModelOrt(TestModelsBase):
    
    model = ort
    
    @classmethod
    def setUpTestData(cls):
        l  = land.objects.create(land_name='Testland', code='TE')
        b = bundesland.objects.create(bland_name='Testbland', land=l, code = 'BL')
        cls.obj1 = ort.objects.create(land = l)
        cls.obj2 = ort.objects.create(stadt='Testort1', land = l)
        cls.obj3 = ort.objects.create(land = l, bland = b)
        cls.obj4 = ort.objects.create(stadt='Testort2', land = l, bland = b)
        cls.test_data = [cls.obj1, cls.obj2, cls.obj3, cls.obj4]
        
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testland')
        self.assertEqual(self.obj2.__str__(), 'Testort1, TE')
        self.assertEqual(self.obj3.__str__(), 'Testbland, TE')
        self.assertEqual(self.obj4.__str__(), 'Testort2, TE-BL')
        
class TestModelDatei(TestModelsBase):
    
    model = datei
    
    @classmethod
    def setUpTestData(cls):
        cls.obj1 = datei.objects.create(titel='Test')
        cls.test_data = [cls.obj1]
    
    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Test')
        
