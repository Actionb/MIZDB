from unittest.mock import patch, Mock

from django.db import models as django_models
from django.test import tag
from django.utils.translation import override as translation_override

import DBentry.m2m as _m2m
import DBentry.models as _models
from DBentry import fields as _fields
from DBentry.base.models import BaseModel
from DBentry.factory import make
from DBentry.tests.base import DataTestCase


class TestBaseModel(DataTestCase):

    model = _models.artikel
    test_data_count = 1

    def test_qs(self):
        self.assertIsInstance(self.obj1.qs(), django_models.QuerySet)
        self.assertEqual(self.obj1.qs().count(), 1)
        self.assertIn(self.obj1, self.obj1.qs())

    def test_qs_exception(self):
        with self.assertRaises(TypeError):
            self.model.qs(self.model)

    def test_str(self):
        # Assert that __str__ just takes the value of the name_field if available
        obj = make(_models.video, titel="lotsa testing", tracks=1, quelle="from the computer")
        self.assertEqual(obj.__str__(), "lotsa testing")
        obj.name_field = "quelle"
        self.assertEqual(obj.__str__(), "from the computer")

        # Assert that, if no name_field is set, __str__ defaults to the old
        # method of gathering values from applicable fields to form a string.
        obj.name_field = None
        self.assertEqual(obj.__str__(), "lotsa testing 1 from the computer")


class TestBaseM2MModel(DataTestCase):

    model = _m2m.m2m_audio_musiker
    raw_data = [{'audio__titel': 'Testaudio', 'musiker__kuenstler_name': 'Alice Test'}]

    def test_str(self):
        # With name_field.
        self.assertEqual(self.obj1.__str__(), "Alice Test")
        # Without name_field.
        self.obj1.name_field = None
        self.assertEqual(self.obj1.__str__(), "Testaudio (Alice Test)")
        # Without 'sufficient' data.
        # Patch get_model_fields so that it only returns one field with null=True.
        # This way the data used to build the string representation out of is
        # empty and __str__ calls super().
        with patch('DBentry.base.models.get_model_fields') as mocked_get_fields:
            with patch.object(BaseModel, '__str__') as mocked_super:
                mocked_get_fields.return_value = [Mock(null=True)]
                self.obj1.__str__()
                self.assertTrue(mocked_super.called)


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
        with patch.object(self.model, 'search_fields', new=['field', '_name']):
            self.assertEqual(self.model.get_search_fields()[0], '_name')

    def test_name_default(self):
        self.assertEqual(str(self.obj1), self.default)

    def test_update_name_notexplodes_on_no_pk_and_forced(self):
        # Unsaved instances should be ignored, as update_name relies on filtering
        # queries with the instance's pk.
        obj = _models.ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name(force_update=True))

    def test_update_name_aborts_on_no_pk(self):
        # Unsaved instances should be ignored, as update_name relies on
        # filtering queries with the instance's pk.
        obj = _models.ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name())

    def test_update_name_aborts_on_name_deferred(self):
        # Do not allow updating the name if it is deferred
        # Pretend as if '_name' is deferred by removing it from __dict__:
        # see get_deferred_fields in django.db.models.base.py
        self.obj2.__dict__.pop('_name')
        self.assertFalse(self.obj2.update_name())

    def test_update_name_on_name_not_deferred(self):
        # Allow updating the name if it is not deferred
        # Pretend as if everything but '_name' is deferred by removing keys from
        # __dict__: see get_deferred_fields in django.db.models.base.py
        keys_to_pop = [
            k
            for k in self.obj2.__dict__.keys()
            #  preserve id and private attributes
            if not (k.startswith('_') or k in ('id', ))
        ]
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

    def test_update_name_resets_change_flag_same_update(self):
        # Assert that the update_name resets the changed flag with the same
        # query that is used to update the name.
        self.obj2._name = 'Beep'
        self.obj2._changed_flag = True
        # One query for the name data required for get_name,
        # another for the update.
        with self.assertNumQueries(2):
            self.assertTrue(self.obj2.update_name())
        self.assertFalse(self.obj2._changed_flag)

    def test_update_name__always_resets_change_flag(self):
        # Even if the _name does not need changing, the _changed_flag should
        # still be set to False.
        self.qs_obj1.update(_changed_flag=True)
        self.obj1.refresh_from_db()
        self.assertFalse(self.obj1.update_name())
        self.assertFalse(self.obj1._changed_flag)

    def test_update_name_does_not_update_with_no_change_flag(self):
        # An update should be skipped if the _changed_flag is False
        self.qs_obj1.update(_name='Beep')
        self.assertFalse(self.obj1.update_name())

    def test_update_name_changed_flag_deferred(self):
        # _changed_flag attribute is deferred, instead of using refresh_from_db,
        # get the value from the database.
        obj = self.qs_obj1.defer('_changed_flag').first()
        with self.assertNumQueries(1):
            obj.update_name()

    def test_save_forces_update(self):
        # save() should update the name even if _changed_flag is False
        self.obj2.beschreibung = 'Testinfo'
        self.obj2.sonderausgabe = True
        self.obj2._changed_flag = False
        self.obj2.save()
        self.assertEqual(
            list(self.qs_obj2.values_list('_name', flat=True)),
            ["Testinfo"]
        )
        self.assertEqual(self.obj2._name, "Testinfo")
        self.assertEqual(str(self.obj2), "Testinfo")


class TestModelArtikel(DataTestCase):

    model = _models.artikel
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

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['schlagzeile', 'zusammenfassung', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'zusammenfassung': 'Zusammenfassung',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelAudio(DataTestCase):

    model = _models.audio
    raw_data = [{'titel': 'Testaudio'}]

    def test_str(self):
        self.assertEqual(self.obj1.__str__(), 'Testaudio')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


@tag("cn")
class TestModelAusgabe(DataTestCase):

    model = _models.ausgabe

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
            'ausgabe_jahr__jahr': ('2020', ),
            'ausgabe_monat__monat__abk': ('Dez', )
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
        name_data = {'ausgabe_jahr__jahr': ('2020', )}
        test_data = [
            ({'ausgabe_monat__monat__abk': ('Dez', )}, "2020-Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabe_lnum__lnum': ('21', )}, "21 (2020)"),
            ({'ausgabe_num__num': ('20', )}, '2020-20'),
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_jahr_multiple_values(self):
        # Check the results of get_name if multiple values for 'jahr'
        # (or other attributes) are given.
        name_data = {'ausgabe_jahr__jahr': ('2021', '2020')}
        test_data = [
            (
                {'ausgabe_monat__monat__abk': ('Jan', 'Dez')},
                "2020/21-Jan/Dez"
            ),
            ({'ausgabe_lnum__lnum': ('22', '21')}, "21/22 (2020/21)"),
            ({'ausgabe_num__num': ('21', '20')}, "2020/21-20/21"),
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_jahrgang(self):
        # Check the results of get_name if 'jahrgang' and no 'jahr' is given.
        name_data = {'jahrgang': ('2', )}
        test_data = [
            ({'ausgabe_monat__monat__abk': ('Dez', )}, "Jg. 2-Dez"),
            ({'ausgabe_monat__monat__abk': ('Jan', 'Dez')}, "Jg. 2-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabe_lnum__lnum': ('21', )}, "21 (Jg. 2)"),
            ({'ausgabe_lnum__lnum': ('22', '21')}, "21/22 (Jg. 2)"),
            ({'ausgabe_num__num': ('20', )}, "Jg. 2-20"),
            ({'ausgabe_num__num': ('21', '20')}, "Jg. 2-20/21")
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_no_jahr_or_jahrgang(self):
        # Check the results of get_name if no 'jahrgang' or 'jahr' is given.
        test_data = [
            ({'ausgabe_monat__monat__abk': ('Dez', )}, "k.A.-Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabe_lnum__lnum': ('21', )}, "21"),
            ({'ausgabe_num__num': ('20', )}, "k.A.-20"),
            ({'ausgabe_monat__monat__abk': ('Jan', 'Dez')}, "k.A.-Jan/Dez"),
            ({'ausgabe_lnum__lnum': ('22', '21')}, "21/22"),
            ({'ausgabe_num__num': ('21', '20')}, "k.A.-20/21")
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
            'ausgabe_jahr__jahr': ('2020', ),
            'ausgabe_monat__monat__abk': ('Dez', ),
            'ausgabe_lnum__lnum': ('21', ),
            'ausgabe_num__num': ('20', ),
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
            'ausgabe_lnum__lnum': ('21', )
        }
        self.assertEqual(
            self.model._get_name(**name_data), '21',
            msg="get_name should just return the lnum if ausgaben_merkmal is"
            " set to lnum and neither jahr nor jahrgang are set."
        )
        name_data = {
            'magazin__ausgaben_merkmal': ('num', ),
            'beschreibung': ('Woops!', )
        }
        self.assertEqual(
            self.model._get_name(**name_data), 'Woops!',
            msg="get_name should ignore ausgaben_merkmal if the attribute "
            "it is referring to is not set."
        )

    @translation_override(language=None)
    def test_get_name_ausgaben_merkmal_multiple_values(self):
        # Check the results of get_name with ausgaben_merkmal override set.
        name_data = {
            'ausgabe_jahr__jahr': ('2021', '2020'),
            'ausgabe_monat__monat__abk': ('Jan', 'Dez'),
            'ausgabe_lnum__lnum': ('22', '21'),
            'ausgabe_num__num': ('21', '20'),
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

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['_name', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelAusgabeJahr(DataTestCase):

    model = _models.ausgabe_jahr

    def test_str(self):
        obj = make(self.model, jahr=2018)
        self.assertEqual(str(obj), '2018')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['jahr'])


class TestModelAusgabeLnum(DataTestCase):

    model = _models.ausgabe_lnum

    def test_str(self):
        obj = make(self.model, lnum=21)
        self.assertEqual(str(obj), '21')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['lnum'])


class TestModelAusgabeMonat(DataTestCase):

    model = _models.ausgabe_monat

    def test_str(self):
        obj = make(self.model, monat__monat='Dezember')
        self.assertEqual(str(obj), 'Dez')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['monat'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['monat__monat', 'monat__abk'])
        )


class TestModelAusgabeNum(DataTestCase):

    model = _models.ausgabe_num

    def test_str(self):
        obj = make(self.model, num=20)
        self.assertEqual(str(obj), '20')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['num'])


@tag("cn")
class TestModelAutor(DataTestCase):

    model = _models.autor

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

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['_name', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelBand(DataTestCase):

    model = _models.band

    def test_str(self):
        obj = make(self.model, band_name='Testband', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Testband')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['band_name'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['band_name', 'band_alias__alias', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'band_alias__alias': 'Alias',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelBandAlias(DataTestCase):

    model = _models.band_alias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelBestand(DataTestCase):
    pass


class TestModelBildmaterial(DataTestCase):

    model = _models.bildmaterial

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelBildreihe(DataTestCase):

    model = _models.Bildreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['name'])


class TestModelBrochure(DataTestCase):

    model = _models.Brochure

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'zusammenfassung': 'Zusammenfassung',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelBuch(DataTestCase):

    model = _models.buch

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelSchriftenreihe(DataTestCase):

    model = _models.schriftenreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['name'])


class TestModelBundesland(DataTestCase):

    model = _models.bundesland

    def test_str(self):
        obj = make(self.model, bland_name='Hessen', code='HE')
        self.assertEqual(str(obj), 'Hessen HE')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land', 'bland_name'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['bland_name', 'code'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(self.model.search_fields_suffixes, {'code': 'Bundesland-Code'})


class TestModelDatei(DataTestCase):

    model = _models.datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelDokument(DataTestCase):

    model = _models.dokument

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


@tag("cn")
class TestModelFormat(DataTestCase):

    model = _models.Format

    @translation_override(language=None)
    def test_get_name(self):
        name_data = {'format_size__size': ('LP', )}
        test_data = [
            ({}, 'LP'),
            ({'anzahl': (1, )}, 'LP'),
            ({'anzahl': (2, )}, '2xLP'),
            ({'channel': ('Mono', )}, '2xLP, Mono'),
            (
                {'tag__tag': ('Compilation', 'Album')},
                '2xLP, Album, Compilation, Mono'
            )
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_uses_format_typ(self):
        # Check that get_name uses 'format_typ__typ' if no 'format_size__size'
        # is given in name_data.
        name_data = {'format_typ__typ': ('Vinyl', )}
        self.assertEqual(self.model._get_name(**name_data), 'Vinyl')
        name_data.update({'format_size__size': ('LP', )})
        self.assertEqual(self.model._get_name(**name_data), 'LP')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['_name'])


class TestModelFormatSize(DataTestCase):

    model = _models.FormatSize

    def test_str(self):
        obj = self.model(size='LP')
        self.assertEqual(str(obj), 'LP')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['size'])


class TestModelFormatTag(DataTestCase):

    model = _models.FormatTag

    def test_str(self):
        obj = self.model(tag='Testtag')
        self.assertEqual(str(obj), 'Testtag')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['tag'])


class TestModelFormatTyp(DataTestCase):

    model = _models.FormatTyp

    def test_str(self):
        obj = self.model(typ='Test')
        self.assertEqual(str(obj), 'Test')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['typ'])


class TestModelGeber(DataTestCase):

    model = _models.geber

    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelGenre(DataTestCase):

    model = _models.Genre

    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['genre'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['genre', 'genrealias__alias'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(self.model.search_fields_suffixes, {'genrealias__alias': 'Alias'})


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

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['herausgeber'])


class TestModelInstrument(DataTestCase):

    model = _models.instrument

    def test_str(self):
        obj = self.model(instrument='Posaune', kuerzel='pos')
        self.assertEqual(str(obj), 'Posaune (pos)')

        obj = self.model(instrument='Posaune', kuerzel='')
        self.assertEqual(str(obj), 'Posaune')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['instrument', 'kuerzel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['instrument', 'kuerzel'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(self.model.search_fields_suffixes, {'kuerzel': 'Kürzel'})


class TestModelKalender(DataTestCase):

    model = _models.Kalendar

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'zusammenfassung': 'Zusammenfassung',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelKatalog(DataTestCase):

    model = _models.Katalog

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'zusammenfassung', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'zusammenfassung': 'Zusammenfassung',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


@tag("cn")
class TestModelLagerort(DataTestCase):

    model = _models.lagerort

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

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['_name', 'ort', 'raum', 'regal', 'fach', 'ordner'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'fach': 'Fach', 'ordner': 'Ordner', 'regal': 'Regal', 'raum': 'Raum'}
        )


class TestModelLand(DataTestCase):

    model = _models.land

    def test_str(self):
        obj = self.model(land_name='Deutschland', code='DE')
        self.assertEqual(str(obj), 'Deutschland DE')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land_name'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['land_name', 'code'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(self.model.search_fields_suffixes, {'code': 'Land-Code'})


class TestModelMagazin(DataTestCase):

    model = _models.magazin

    def test_str(self):
        obj = self.model(magazin_name='Testmagazin')
        self.assertEqual(str(obj), 'Testmagazin')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['magazin_name'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['magazin_name', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelMemorabilien(DataTestCase):

    model = _models.memorabilien

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelMonat(DataTestCase):

    model = _models.monat

    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['ordinal'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['monat', 'abk', 'ordinal'])
        )

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelMusiker(DataTestCase):

    model = _models.Musiker

    def test_str(self):
        obj = self.model(
            kuenstler_name='Alice Tester', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Alice Tester')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['kuenstler_name'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['kuenstler_name', 'musikeralias__alias', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'musikeralias__alias': 'Alias',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelMusikerAlias(DataTestCase):

    model = _models.MusikerAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


@tag("cn")
class TestModelOrt(DataTestCase):

    model = _models.ort

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

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['_name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


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

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['_name', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


class TestModelPlattenfirma(DataTestCase):

    model = _models.plattenfirma

    def test_str(self):
        obj = self.model(name='Testfirma')
        self.assertEqual(str(obj), 'Testfirma')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelProvenienz(DataTestCase):

    model = _models.provenienz

    def test_str(self):
        obj = make(self.model, geber__name='TestGeber', typ='Fund')
        self.assertEqual(str(obj), 'TestGeber (Fund)')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['geber', 'typ'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['geber__name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelSchlagwort(DataTestCase):

    model = _models.schlagwort

    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['schlagwort'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['schlagwort', 'schlagwort_alias__alias'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes, {'schlagwort_alias__alias': 'Alias'})


class TestModelSchlagwortAlias(DataTestCase):

    model = _models.schlagwort_alias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelSpielort(DataTestCase):

    model = _models.spielort

    def test_str(self):
        land_object = _models.land.objects.create(land_name='Deutschland', code='DE')
        obj = self.model(
            name='Testspielort', ort=_models.ort.objects.create(land=land_object))
        self.assertEqual(str(obj), 'Testspielort')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name', 'ort'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['name', 'spielort_alias__alias', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'spielort_alias__alias': 'Alias',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelSpielortAlias(DataTestCase):

    model = _models.spielort_alias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelTechnik(DataTestCase):

    model = _models.technik

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )


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

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name', 'datum', 'spielort'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['name', 'datum', 'veranstaltung_alias__alias', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {
                'datum': 'Datum',
                'veranstaltung_alias__alias': 'Alias',
                'beschreibung': 'Beschreibung',
                'bemerkungen': 'Bemerkungen'
            }
        )


class TestModelVeranstaltungAlias(DataTestCase):

    model = _models.veranstaltung_alias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


class TestModelVeranstaltungsreihe(DataTestCase):

    model = _models.Veranstaltungsreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelVerlag(DataTestCase):

    model = _models.verlag

    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['verlag_name', 'sitz'])

    def test_get_search_fields(self):
        self.assertEqual(self.model.get_search_fields(), ['verlag_name'])

    def test_search_fields_suffixes(self):
        self.assertFalse(self.model.search_fields_suffixes)


class TestModelVideo(DataTestCase):

    model = _models.video

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_get_search_fields(self):
        self.assertEqual(
            sorted(self.model.get_search_fields()),
            sorted(['titel', 'beschreibung', 'bemerkungen'])
        )

    def test_search_fields_suffixes(self):
        self.assertEqual(
            self.model.search_fields_suffixes,
            {'beschreibung': 'Beschreibung', 'bemerkungen': 'Bemerkungen'}
        )
