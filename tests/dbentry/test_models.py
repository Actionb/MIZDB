
class TestModelArtikel(DataTestCase):

    model = _models.Artikel
    test_data_count = 1

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), str(self.obj1.schlagzeile))
        self.obj1.schlagzeile = ''
        self.assertEqual(self.obj1.__str__(), 'Keine Schlagzeile gegeben!')
        self.obj1.zusammenfassung = (
            'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.')
        self.assertEqual(
            self.obj1.__str__(),
            'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.'
        )

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(
            self.model._meta.ordering,
            ['ausgabe__magazin__magazin_name', 'ausgabe___name', 'seite', 'schlagzeile']
        )


class TestModelAudio(DataTestCase):

    model = _models.Audio
    raw_data = [{'titel': 'Testaudio'}]

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testaudio')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


@tag("cn")
class TestModelAusgabe(DataTestCase):

    model = _models.Ausgabe

    @translation_override(language=None)
    def test_get_name_sonderausgabe(self):
        # Check the results of get_name when sonderausgabe == True.
        # sonderausgabe + beschreibung => beschreibung
        name_data = {'sonderausgabe': (True, ), 'beschreibung': ('Test-Info', )}
        self.assertEqual(
            self.model._get_name(**name_data),
            'Test-Info',
            msg='sonderausgabe + beschreibung => beschreibung'
        )
        # sonderausgabe + beschreibung + any other data => beschreibung
        name_data.update({
            'jahrgang': ('2', ),
            'ausgabejahr__jahr': ('2020', ),
            'ausgabemonat__monat__abk': ('Dez', )
        })
        self.assertEqual(
            self.model._get_name(**name_data),
            'Test-Info',
            msg='sonderausgabe + beschreibung + any other data => beschreibung'
        )
        name_data['sonderausgabe'] = (False, )
        self.assertNotEqual(
            self.model._get_name(**name_data),
            'Test-Info',
            msg=(
                'With sonderausgabe=False, the name should not be according to '
                'beschreibung.'
            )
        )

    @translation_override(language=None)
    def test_get_name_jahr(self):
        # Check the results of get_name if 'jahr' is given.
        base_data = {'ausgabejahr__jahr': ('2020', )}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez', )}, "2020-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "2020-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1', )}, "01 (2020)"),
            ({'ausgabelnum__lnum': ('21', )}, "21 (2020)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (2020)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (2020)"),
            ({'ausgabenum__num': ('2', )}, '2020-02'),
            ({'ausgabenum__num': ('22', )}, '2020-22'),
            ({'ausgabenum__num': ('1', 2)}, '2020-01/02'),
            ({'ausgabenum__num': ('21', 20)}, "2020-20/21"),
        ]
        for update, expected in test_data:
            name_data = {**base_data, **update}
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_jahr_multiple_values(self):
        # Check the results of get_name if multiple values for 'jahr'
        # (or other attributes) are given.
        base_data = {'ausgabejahr__jahr': ('2021', 2020)}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez', )}, "2020/21-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "2020/21-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1', )}, "01 (2020/21)"),
            ({'ausgabelnum__lnum': ('21', )}, "21 (2020/21)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (2020/21)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (2020/21)"),
            ({'ausgabenum__num': ('2', )}, '2020/21-02'),
            ({'ausgabenum__num': ('22', )}, '2020/21-22'),
            ({'ausgabenum__num': ('1', 2)}, '2020/21-01/02'),
            ({'ausgabenum__num': ('21', 20)}, "2020/21-20/21"),
        ]
        for update, expected in test_data:
            name_data = {**base_data, **update}
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_jahrgang(self):
        # Check the results of get_name if 'jahrgang' and no 'jahr' is given.
        base_data = {'jahrgang': ('2', )}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez', )}, "Jg. 2-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "Jg. 2-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1', )}, "01 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('21', )}, "21 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (Jg. 2)"),
            ({'ausgabenum__num': ('2', )}, 'Jg. 2-02'),
            ({'ausgabenum__num': ('22', )}, 'Jg. 2-22'),
            ({'ausgabenum__num': ('1', 2)}, 'Jg. 2-01/02'),
            ({'ausgabenum__num': ('21', 20)}, "Jg. 2-20/21"),
        ]
        for update, expected in test_data:
            name_data = {**base_data, **update}
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_no_jahr_or_jahrgang(self):
        # Check the results of get_name if no 'jahrgang' or 'jahr' is given.
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez', )}, "k.A.-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "k.A.-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1', )}, "01"),
            ({'ausgabelnum__lnum': ('21', )}, "21"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22"),
            ({'ausgabenum__num': ('2', )}, 'k.A.-02'),
            ({'ausgabenum__num': ('22', )}, 'k.A.-22'),
            ({'ausgabenum__num': ('1', 2)}, 'k.A.-01/02'),
            ({'ausgabenum__num': ('21', 20)}, "k.A.-20/21"),
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_no_data(self):
        # Check the results of get_name if no or little data is given.
        test_data = [
            ({}, 'No data for Ausgabe.'),
            ({'beschreibung': ('Test-Info', )}, 'Test-Info')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_ausgaben_merkmal(self):
        # Check the results of get_name with ausgaben_merkmal override set.
        name_data = {
            'ausgabejahr__jahr': ('2020', ),
            'ausgabemonat__monat__abk': ('Dez', ),
            'ausgabelnum__lnum': ('21', ),
            'ausgabenum__num': ('20', ),
            'e_datum': ('02.05.2018', ),
        }
        test_data = [
            ('e_datum', '02.05.2018'),
            ('monat', '2020-Dez'),
            ('num', '2020-20'),
            ('lnum', '21 (2020)'),
        ]
        for merkmal, expected in test_data:
            name_data['magazin__ausgaben_merkmal'] = (merkmal, )
            with self.subTest(merkmal=merkmal):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

        # Some edge case tests:
        name_data = {
            'magazin__ausgaben_merkmal': ('lnum', ),
            'ausgabelnum__lnum': ('21', )
        }
        self.assertEqual(
            self.model._get_name(**name_data), '21',
            msg="get_name should just return the lnum if ausgaben_merkmal is"
            " set to lnum and neither jahr nor jahrgang are set."
        )
        name_data = {
            'magazin__ausgaben_merkmal': ('num', ),
            'beschreibung': ('Whoops!', )
        }
        self.assertEqual(
            self.model._get_name(**name_data), 'Whoops!',
            msg="get_name should ignore ausgaben_merkmal if the attribute "
            "it is referring to is not set."
        )

    @translation_override(language=None)
    def test_get_name_ausgaben_merkmal_multiple_values(self):
        # Check the results of get_name with ausgaben_merkmal override set.
        name_data = {
            'ausgabejahr__jahr': ('2021', '2020'),
            'ausgabemonat__monat__abk': ('Jan', 'Dez'),
            'ausgabelnum__lnum': ('22', '21'),
            'ausgabenum__num': ('21', '20'),
        }
        test_data = [
            ('monat', '2020/21-Jan/Dez'),
            ('num', '2020/21-20/21'),
            ('lnum', '21/22 (2020/21)'),
        ]
        for merkmal, expected in test_data:
            name_data['magazin__ausgaben_merkmal'] = (merkmal, )
            with self.subTest(merkmal=merkmal):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['magazin'])


class TestModelAusgabeJahr(DataTestCase):

    model = _models.AusgabeJahr

    def test_str(self):
        obj = make(self.model, jahr=2018)
        self.assertEqual(str(obj), '2018')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['jahr'])


class TestModelAusgabeLnum(DataTestCase):

    model = _models.AusgabeLnum

    def test_str(self):
        obj = make(self.model, lnum=21)
        self.assertEqual(str(obj), '21')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['lnum'])


class TestModelAusgabeMonat(DataTestCase):

    model = _models.AusgabeMonat

    def test_str(self):
        obj = make(self.model, monat__monat='Dezember')
        self.assertEqual(str(obj), 'Dez')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['monat'])


class TestModelAusgabeNum(DataTestCase):

    model = _models.AusgabeNum

    def test_str(self):
        obj = make(self.model, num=20)
        self.assertEqual(str(obj), '20')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['num'])


@tag("cn")
class TestModelAutor(DataTestCase):

    model = _models.Autor

    @translation_override(language=None)
    def test_get_name(self):
        test_data = [
            ({'person___name': ('Alice Tester', )}, 'Alice Tester'),
            ({'kuerzel': ('TK', )}, 'TK'),
            ({'person___name': ('Alice Tester', ), 'kuerzel': ('TK', )}, 'Alice Tester (TK)'),
            ({}, 'No data for Autor.'),
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_ignores_default_person(self):
        # get_name should ignore default values for person.
        test_data = [
            ({'person___name': ('No data for Person.', ), 'kuerzel': ('TK', )},  'TK'),
            ({'person___name': ('unbekannt', ), 'kuerzel': ('TK', )}, 'TK')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['_name'])


class TestModelBand(DataTestCase):

    model = _models.Band

    def test_str(self):
        obj = make(self.model, band_name='Testband', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Testband')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['band_name'])


class TestModelBandAlias(DataTestCase):

    model = _models.BandAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelBestand(DataTestCase):

    model = _models.Bestand

    def test_bestand_object(self):
        # Assert that the property 'bestand_object' returns the expected
        # instance: the object the Bestand instance is meant to keep a record
        # of.
        test_data = [
            ('ausgabe', _models.Ausgabe),
            ('audio', _models.Audio),
            ('brochure', _models.Katalog)
        ]
        lagerort = make(_models.Lagerort)
        for field_name, expected_model in test_data:
            with self.subTest(field_name=field_name):
                obj = _models.Bestand.objects.create(
                    **{'lagerort': lagerort, field_name: make(expected_model)})
                # refresh to clear Bestand.brochure cache so that it doesn't
                # return the Katalog instance directly.
                obj.refresh_from_db()
                self.assertIsInstance(obj.bestand_object, expected_model)


class TestModelPlakat(DataTestCase):

    model = _models.Plakat

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelBildreihe(DataTestCase):

    model = _models.Bildreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


class TestModelBrochure(DataTestCase):

    model = _models.Brochure

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelBuch(DataTestCase):

    model = _models.Buch

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelSchriftenreihe(DataTestCase):

    model = _models.Schriftenreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


class TestModelBundesland(DataTestCase):

    model = _models.Bundesland

    def test_str(self):
        obj = make(self.model, bland_name='Hessen', code='HE')
        self.assertEqual(str(obj), 'Hessen HE')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land', 'bland_name'])


class TestModelDatei(DataTestCase):

    model = _models.Datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelDokument(DataTestCase):

    model = _models.Dokument

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelGeber(DataTestCase):

    model = _models.Geber

    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name'])


class TestModelGenre(DataTestCase):

    model = _models.Genre

    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['genre'])


class TestModelGenreAlias(DataTestCase):

    model = _models.GenreAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelHerausgeber(DataTestCase):

    model = _models.Herausgeber

    def test_str(self):
        obj = self.model(herausgeber='Testherausgeber')
        self.assertEqual(str(obj), 'Testherausgeber')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['herausgeber'])


class TestModelInstrument(DataTestCase):

    model = _models.Instrument

    def test_str(self):
        obj = self.model(instrument='Posaune', kuerzel='pos')
        self.assertEqual(str(obj), 'Posaune (pos)')

        obj = self.model(instrument='Posaune', kuerzel='')
        self.assertEqual(str(obj), 'Posaune')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['instrument', 'kuerzel'])


class TestModelKalender(DataTestCase):

    model = _models.Kalender

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelKatalog(DataTestCase):

    model = _models.Katalog

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


@tag("cn")
class TestModelLagerort(DataTestCase):

    model = _models.Lagerort

    @translation_override(language=None)
    def test_get_name(self):
        name_data = {'ort': ('Testort', )}
        test_data = [
            ({}, 'Testort'),
            ({'regal': ('Testregal', )}, 'Testregal (Testort)'),
            ({'fach': ('12', )}, "Testregal-12 (Testort)")
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_with_raum(self):
        name_data = {'ort': ('Testort', ), 'raum': ('Testraum', )}
        test_data = [
            ({}, 'Testraum (Testort)'),
            ({'regal': ('Testregal', )}, 'Testraum-Testregal (Testort)'),
            ({'fach': ('12', )}, "Testraum-Testregal-12 (Testort)")
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['_name'])


class TestModelLand(DataTestCase):

    model = _models.Land

    def test_str(self):
        obj = self.model(land_name='Deutschland', code='DE')
        self.assertEqual(str(obj), 'Deutschland DE')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land_name'])

class TestModelMagazin(DataTestCase):

    model = _models.Magazin

    def test_str(self):
        obj = self.model(magazin_name='Testmagazin')
        self.assertEqual(str(obj), 'Testmagazin')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['magazin_name'])


class TestModelMemorabilien(DataTestCase):

    model = _models.Memorabilien

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelMonat(DataTestCase):

    model = _models.Monat

    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['ordinal'])


class TestModelMusiker(DataTestCase):

    model = _models.Musiker

    def test_str(self):
        obj = self.model(
            kuenstler_name='Alice Tester', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Alice Tester')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['kuenstler_name'])

class TestModelMusikerAlias(DataTestCase):

    model = _models.MusikerAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


@tag("cn")
class TestModelOrt(DataTestCase):

    model = _models.Ort

    @translation_override(language=None)
    def test_get_name(self):
        name_data = {'land__land_name': ('Deutschland', )}
        test_data = [
            ({}, 'Deutschland'),
            ({'land__code': ('DE', ), 'bland__bland_name': ('Hessen', )}, 'Hessen, DE'),
            ({'stadt': ('Kassel', )}, 'Kassel, DE'),
            ({'bland__code': ('HE', )}, 'Kassel, DE-HE')
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land', 'bland', 'stadt'])


@tag("cn")
class TestModelPerson(DataTestCase):

    model = _models.Person

    @translation_override(language=None)
    def test_get_name(self):
        test_data = [
            ({'vorname': ('', )}, 'No data for Person.'),
            ({'nachname': ('', )}, 'No data for Person.'),
            ({'vorname': ('', ), 'nachname': ('', )}, 'No data for Person.'),
            ({'vorname': ('', ), 'nachname': ('Test', )}, 'Test'),
            ({'vorname': ('Beep', ), 'nachname': ('Boop', )}, 'Beep Boop')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['_name'])


class TestModelPlattenfirma(DataTestCase):

    model = _models.Plattenfirma

    def test_str(self):
        obj = self.model(name='Testfirma')
        self.assertEqual(str(obj), 'Testfirma')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name'])


class TestModelProvenienz(DataTestCase):

    model = _models.Provenienz

    def test_str(self):
        obj = make(self.model, geber__name='TestGeber', typ='Fund')
        self.assertEqual(str(obj), 'TestGeber (Fund)')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['geber', 'typ'])


class TestModelSchlagwort(DataTestCase):

    model = _models.Schlagwort

    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['schlagwort'])


class TestModelSchlagwortAlias(DataTestCase):

    model = _models.SchlagwortAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelSpielort(DataTestCase):

    model = _models.Spielort

    def test_str(self):
        land_object = _models.Land.objects.create(land_name='Deutschland', code='DE')
        obj = self.model(
            name='Testspielort', ort=_models.Ort.objects.create(land=land_object))
        self.assertEqual(str(obj), 'Testspielort')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name', 'ort'])


class TestModelSpielortAlias(DataTestCase):

    model = _models.SpielortAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelTechnik(DataTestCase):

    model = _models.Technik

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelVeranstaltung(DataTestCase):

    model = _models.Veranstaltung

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name', 'datum', 'spielort'])


class TestModelVeranstaltungAlias(DataTestCase):

    model = _models.VeranstaltungAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelVeranstaltungsreihe(DataTestCase):

    model = _models.Veranstaltungsreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


class TestModelVerlag(DataTestCase):

    model = _models.Verlag

    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['verlag_name', 'sitz'])


class TestModelVideo(DataTestCase):

    model = _models.Video

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


class TestModelBaseBrochure(DataTestCase):

    model = _models.BaseBrochure

    def test_resolve_child_no_children(self):
        # Should the obj have no children, None should be returned.
        obj = make(self.model)
        self.assertIsNone(obj.resolve_child())

    def test_resolve_child(self):
        child_models = (_models.Brochure, _models.Kalender, _models.Katalog)
        for child_model in child_models:
            with self.subTest(child_model=child_model._meta.object_name):
                obj = make(child_model)
                # Call resolve_child from the BaseBrochure parent instance.
                resolved = getattr(obj, child_model._meta.pk.name).resolve_child()
                self.assertIsInstance(resolved, child_model)


class TestModelFoto(DataTestCase):

    model = _models.Foto

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])
