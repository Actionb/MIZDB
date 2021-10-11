from unittest.mock import patch, Mock

from django.core import checks
from django.db import models as django_models
from django.test import tag
from django.utils.translation import override as translation_override

import dbentry.m2m as _m2m
import dbentry.models as _models
from dbentry import fields as _fields
from dbentry.base.models import BaseModel
from dbentry.factory import make
from dbentry.tests.base import DataTestCase


# noinspection PyUnresolvedReferences
class TestBaseModel(DataTestCase):

    model = _models.Artikel
    test_data_count = 1

    def test_qs(self):
        self.assertIsInstance(self.obj1.qs(), django_models.QuerySet)
        self.assertEqual(self.obj1.qs().count(), 1)
        self.assertIn(self.obj1, self.obj1.qs())

    def test_qs_exception(self):
        with self.assertRaises(TypeError):
            # noinspection PyTypeChecker
            self.model.qs(self.model)

    # noinspection SpellCheckingInspection
    def test_str(self):
        # Assert that __str__ just takes the value of the name_field if available
        obj = make(_models.Video, titel="lotsa testing", quelle="from the computer", medium_qty=0)
        self.assertEqual(obj.__str__(), "lotsa testing")
        obj.name_field = "quelle"
        self.assertEqual(obj.__str__(), "from the computer")

        # Assert that, if no name_field is set, __str__ defaults to the old
        # method of gathering values from applicable fields to form a string.
        obj.name_field = None
        self.assertEqual(obj.__str__(), "lotsa testing from the computer")


# noinspection PyUnresolvedReferences
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
        with patch('dbentry.base.models.get_model_fields') as mocked_get_fields:
            with patch.object(BaseModel, '__str__') as mocked_super:
                mocked_get_fields.return_value = [Mock(null=True)]
                self.obj1.__str__()
                self.assertTrue(mocked_super.called)


@tag("cn")
class TestComputedNameModel(DataTestCase):

    model = _models.Ausgabe
    default = model._name_default % {'verbose_name': model._meta.verbose_name}

    @classmethod
    def setUpTestData(cls):
        cls.mag = make(_models.Magazin)
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

    def test_name_default(self):
        self.assertEqual(str(self.obj1), self.default)

    def test_update_name_no_pk_and_forced(self):
        # Unsaved instances should be ignored, as update_name relies on filtering
        # queries with the instance's pk.
        obj = _models.Ausgabe(magazin=self.mag)
        self.assertFalse(obj.update_name(force_update=True))

    def test_update_name_aborts_on_no_pk(self):
        # Unsaved instances should be ignored, as update_name relies on
        # filtering queries with the instance's pk.
        obj = _models.Ausgabe(magazin=self.mag)
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

    def test_check_name_composing_fields(self):
        # Assert that _check_name_composing_fields identifies invalid fields in
        # 'name_composing_fields'.
        msg_template = "Attribute 'name_composing_fields' contains invalid item: '%s'. %s"
        with patch.object(self.model, 'name_composing_fields'):
            # Invalid field:
            self.model.name_composing_fields = ['beep']
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % ('beep', "Ausgabe has no field named 'beep'")
            )
            # Invalid lookup:
            self.model.name_composing_fields = ['magazin__year']
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Error)
            self.assertEqual(
                errors[0].msg,
                msg_template % ('magazin__year', "Invalid lookup: year for ForeignKey.")
            )

    def test_check_name_composing_fields_no_attribute(self):
        # Assert that _check_name_composing_fields issues a warning if the
        # attribute 'name_composing_fields' is not set.
        with patch.object(self.model, 'name_composing_fields', new=None):
            errors = self.model._check_name_composing_fields()
            self.assertTrue(errors)
            self.assertEqual(len(errors), 1)
            self.assertIsInstance(errors[0], checks.Warning)
            self.assertEqual(
                errors[0].msg,
                "You must specify the fields that make up the name by " 
                "listing them in name_composing_fields."
            )


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
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
        name_data = {'ausgabejahr__jahr': ('2020', )}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez', )}, "2020-Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('21', )}, "21 (2020)"),
            ({'ausgabenum__num': ('20', )}, '2020-20'),
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
        name_data = {'ausgabejahr__jahr': ('2021', '2020')}
        test_data = [
            (
                {'ausgabemonat__monat__abk': ('Jan', 'Dez')},
                "2020/21-Jan/Dez"
            ),
            ({'ausgabelnum__lnum': ('22', '21')}, "21/22 (2020/21)"),
            ({'ausgabenum__num': ('21', '20')}, "2020/21-20/21"),
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
            ({'ausgabemonat__monat__abk': ('Dez', )}, "Jg. 2-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "Jg. 2-Jan/Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('21', )}, "21 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('22', '21')}, "21/22 (Jg. 2)"),
            ({'ausgabenum__num': ('20', )}, "Jg. 2-20"),
            ({'ausgabenum__num': ('21', '20')}, "Jg. 2-20/21")
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
            ({'ausgabemonat__monat__abk': ('Dez', )}, "k.A.-Dez"),
            ({'e_datum': ('02.05.2018', )}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('21', )}, "21"),
            ({'ausgabenum__num': ('20', )}, "k.A.-20"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "k.A.-Jan/Dez"),
            ({'ausgabelnum__lnum': ('22', '21')}, "21/22"),
            ({'ausgabenum__num': ('21', '20')}, "k.A.-20/21")
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


# noinspection PyUnresolvedReferences
class TestModelAusgabeJahr(DataTestCase):

    model = _models.AusgabeJahr

    def test_str(self):
        obj = make(self.model, jahr=2018)
        self.assertEqual(str(obj), '2018')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['jahr'])


# noinspection PyUnresolvedReferences
class TestModelAusgabeLnum(DataTestCase):

    model = _models.AusgabeLnum

    def test_str(self):
        obj = make(self.model, lnum=21)
        self.assertEqual(str(obj), '21')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['lnum'])


# noinspection PyUnresolvedReferences
class TestModelAusgabeMonat(DataTestCase):

    model = _models.AusgabeMonat

    def test_str(self):
        obj = make(self.model, monat__monat='Dezember')
        self.assertEqual(str(obj), 'Dez')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['monat'])


# noinspection PyUnresolvedReferences
class TestModelAusgabeNum(DataTestCase):

    model = _models.AusgabeNum

    def test_str(self):
        obj = make(self.model, num=20)
        self.assertEqual(str(obj), '20')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['num'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelBand(DataTestCase):

    model = _models.Band

    def test_str(self):
        obj = make(self.model, band_name='Testband', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Testband')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['band_name'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelPlakat(DataTestCase):

    model = _models.Plakat

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelBildreihe(DataTestCase):

    model = _models.Bildreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


# noinspection PyUnresolvedReferences
class TestModelBrochure(DataTestCase):

    model = _models.Brochure

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelBuch(DataTestCase):

    model = _models.Buch

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelSchriftenreihe(DataTestCase):

    model = _models.Schriftenreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


# noinspection PyUnresolvedReferences
class TestModelBundesland(DataTestCase):

    model = _models.Bundesland

    def test_str(self):
        obj = make(self.model, bland_name='Hessen', code='HE')
        self.assertEqual(str(obj), 'Hessen HE')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['land', 'bland_name'])


# noinspection PyUnresolvedReferences
class TestModelDatei(DataTestCase):

    model = _models.Datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelDokument(DataTestCase):

    model = _models.Dokument

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelGeber(DataTestCase):

    model = _models.Geber

    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['name'])


# noinspection PyUnresolvedReferences
class TestModelGenre(DataTestCase):

    model = _models.Genre

    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['genre'])


# noinspection PyUnresolvedReferences
class TestModelGenreAlias(DataTestCase):

    model = _models.GenreAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


# noinspection PyUnresolvedReferences
class TestModelHerausgeber(DataTestCase):

    model = _models.Herausgeber

    def test_str(self):
        obj = self.model(herausgeber='Testherausgeber')
        self.assertEqual(str(obj), 'Testherausgeber')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['herausgeber'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelKalender(DataTestCase):

    model = _models.Kalender

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelKatalog(DataTestCase):

    model = _models.Katalog

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelMemorabilien(DataTestCase):

    model = _models.Memorabilien

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelMonat(DataTestCase):

    model = _models.Monat

    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['ordinal'])


# noinspection PyUnresolvedReferences
class TestModelMusiker(DataTestCase):

    model = _models.Musiker

    def test_str(self):
        obj = self.model(
            kuenstler_name='Alice Tester', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Alice Tester')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['kuenstler_name'])

# noinspection PyUnresolvedReferences
class TestModelMusikerAlias(DataTestCase):

    model = _models.MusikerAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelProvenienz(DataTestCase):

    model = _models.Provenienz

    def test_str(self):
        obj = make(self.model, geber__name='TestGeber', typ='Fund')
        self.assertEqual(str(obj), 'TestGeber (Fund)')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['geber', 'typ'])


# noinspection PyUnresolvedReferences
class TestModelSchlagwort(DataTestCase):

    model = _models.Schlagwort

    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['schlagwort'])


# noinspection PyUnresolvedReferences
class TestModelSchlagwortAlias(DataTestCase):

    model = _models.SchlagwortAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelSpielortAlias(DataTestCase):

    model = _models.SpielortAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


# noinspection PyUnresolvedReferences
class TestModelTechnik(DataTestCase):

    model = _models.Technik

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
class TestModelVeranstaltung(DataTestCase):

    model = _models.Veranstaltung

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


# noinspection PyUnresolvedReferences
class TestModelVeranstaltungAlias(DataTestCase):

    model = _models.VeranstaltungAlias

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['alias'])


# noinspection PyUnresolvedReferences
class TestModelVeranstaltungsreihe(DataTestCase):

    model = _models.Veranstaltungsreihe

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['name'])


# noinspection PyUnresolvedReferences
class TestModelVerlag(DataTestCase):

    model = _models.Verlag

    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['verlag_name', 'sitz'])


# noinspection PyUnresolvedReferences
class TestModelVideo(DataTestCase):

    model = _models.Video

    def test_meta_ordering(self):
        self.assertEqual(self.model._meta.ordering, ['titel'])


# noinspection PyUnresolvedReferences
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


# noinspection PyUnresolvedReferences
class TestModelFoto(DataTestCase):

    model = _models.Foto

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        # Check the default ordering of this model.
        self.assertEqual(self.model._meta.ordering, ['titel'])
