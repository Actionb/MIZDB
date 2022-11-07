from django.utils.translation import override as translation_override

from dbentry import m2m as _m2m
from dbentry import models as _models
from dbentry.fts.query import SIMPLE, STEMMING
from tests.case import MIZTestCase
from tests.factory import make


def get_search_field_columns(field):
    """Return the columns of the given SearchVectorField."""
    return {c.name: c.__dict__.copy() for c in field.columns}


class TestModelPerson(MIZTestCase):
    model = _models.Person

    @translation_override(language=None)
    def test_get_name(self):
        test_data = [
            ({'vorname': ('',)}, 'No data for Person.'),
            ({'nachname': ('',)}, 'No data for Person.'),
            ({'vorname': ('',), 'nachname': ('',)}, 'No data for Person.'),
            ({'vorname': ('',), 'nachname': ('Test',)}, 'Test'),
            ({'vorname': ('Beep',), 'nachname': ('Boop',)}, 'Beep Boop')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['_name'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('_name', ('_name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelMusiker(MIZTestCase):
    model = _models.Musiker

    def test_str(self):
        obj = self.model(
            kuenstler_name='Alice Tester', beschreibung='Beep', bemerkungen='Boop'
        )
        self.assertEqual(str(obj), 'Alice Tester')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['kuenstler_name'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('kuenstler_name', ('kuenstler_name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelMusikerAlias(MIZTestCase):
    model = _models.MusikerAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'B')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelGenre(MIZTestCase):
    model = _models.Genre

    def test_str(self):
        obj = self.model(genre='Testgenre')
        self.assertEqual(str(obj), 'Testgenre')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['genre'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('genre', columns)
        self.assertEqual(columns['genre']['name'], 'genre')
        self.assertEqual(columns['genre']['weight'], 'A')
        self.assertEqual(columns['genre']['language'], SIMPLE)


class TestModelGenreAlias(MIZTestCase):
    model = _models.GenreAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'B')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelBand(MIZTestCase):
    model = _models.Band

    def test_str(self):
        obj = make(self.model, band_name='Testband', beschreibung='Beep', bemerkungen='Boop')
        self.assertEqual(str(obj), 'Testband')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['band_name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('band_name', ('band_name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('bandalias___fts', SIMPLE), self.model.related_search_vectors)


class TestModelBandAlias(MIZTestCase):
    model = _models.BandAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'B')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelAutor(MIZTestCase):
    model = _models.Autor

    @translation_override(language=None)
    def test_get_name(self):
        test_data = [
            ({'person___name': ('Alice Tester',)}, 'Alice Tester'),
            ({'kuerzel': ('TK',)}, 'TK'),
            ({'person___name': ('Alice Tester',), 'kuerzel': ('TK',)}, 'Alice Tester (TK)'),
            ({}, 'No data for Autor.'),
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_ignores_default_person(self):
        """get_name should ignore default values for person."""
        test_data = [
            ({'person___name': ('No data for Person.',), 'kuerzel': ('TK',)}, 'TK'),
            ({'person___name': ('unbekannt',), 'kuerzel': ('TK',)}, 'TK')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['_name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('_name', ('_name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('person___fts', SIMPLE), self.model.related_search_vectors)


class TestModelAusgabe(MIZTestCase):
    model = _models.Ausgabe

    @translation_override(language=None)
    def test_get_name_sonderausgabe(self):
        """If sonderausgabe is True, get_name should return the 'beschreibung'."""
        """Check the results of get_name when sonderausgabe == True."""
        # sonderausgabe + beschreibung => beschreibung
        name_data = {'sonderausgabe': (True,), 'beschreibung': ('Test-Info',)}
        self.assertEqual(self.model._get_name(**name_data), 'Test-Info')

        # sonderausgabe + beschreibung + any other data => beschreibung
        name_data.update(
            {
                'jahrgang': ('2',),
                'ausgabejahr__jahr': ('2020',),
                'ausgabemonat__monat__abk': ('Dez',)
            }
        )
        self.assertEqual(self.model._get_name(**name_data), 'Test-Info')

        # sonderausgabe is False and other data is available: the value of
        # beschreibung should not be the result of get_name.
        name_data['sonderausgabe'] = (False,)
        self.assertNotEqual(self.model._get_name(**name_data), 'Test-Info')

    @translation_override(language=None)
    def test_get_name_jahr(self):
        """Check the results of get_name, if 'jahr' is given."""
        base_data = {'ausgabejahr__jahr': ('2020',)}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez',)}, "2020-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "2020-Jan/Dez"),
            ({'e_datum': ('02.05.2018',)}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1',)}, "01 (2020)"),
            ({'ausgabelnum__lnum': ('21',)}, "21 (2020)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (2020)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (2020)"),
            ({'ausgabenum__num': ('2',)}, '2020-02'),
            ({'ausgabenum__num': ('22',)}, '2020-22'),
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
        """
        Check the results of get_name, if multiple values for 'jahr' (or other
        attributes) are given.
        """
        base_data = {'ausgabejahr__jahr': ('2021', 2020)}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez',)}, "2020/21-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "2020/21-Jan/Dez"),
            ({'e_datum': ('02.05.2018',)}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1',)}, "01 (2020/21)"),
            ({'ausgabelnum__lnum': ('21',)}, "21 (2020/21)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (2020/21)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (2020/21)"),
            ({'ausgabenum__num': ('2',)}, '2020/21-02'),
            ({'ausgabenum__num': ('22',)}, '2020/21-22'),
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
        """Check the results of get_name, if 'jahrgang' and no 'jahr' is given."""
        base_data = {'jahrgang': ('2',)}
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez',)}, "Jg. 2-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "Jg. 2-Jan/Dez"),
            ({'e_datum': ('02.05.2018',)}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1',)}, "01 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('21',)}, "21 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02 (Jg. 2)"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22 (Jg. 2)"),
            ({'ausgabenum__num': ('2',)}, 'Jg. 2-02'),
            ({'ausgabenum__num': ('22',)}, 'Jg. 2-22'),
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
        """Check the results of get_name, if no 'jahrgang' or 'jahr' is given."""
        test_data = [
            ({'ausgabemonat__monat__abk': ('Dez',)}, "k.A.-Dez"),
            ({'ausgabemonat__monat__abk': ('Jan', 'Dez')}, "k.A.-Jan/Dez"),
            ({'e_datum': ('02.05.2018',)}, '02.05.2018'),
            ({'ausgabelnum__lnum': ('1',)}, "01"),
            ({'ausgabelnum__lnum': ('21',)}, "21"),
            ({'ausgabelnum__lnum': ('1', 2)}, "01/02"),
            ({'ausgabelnum__lnum': ('22', 21)}, "21/22"),
            ({'ausgabenum__num': ('2',)}, 'k.A.-02'),
            ({'ausgabenum__num': ('22',)}, 'k.A.-22'),
            ({'ausgabenum__num': ('1', 2)}, 'k.A.-01/02'),
            ({'ausgabenum__num': ('21', 20)}, "k.A.-20/21"),
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_no_data(self):
        """Check the results of get_name if none or only minimal data is given."""
        test_data = [
            ({}, 'No data for Ausgabe.'),
            ({'beschreibung': ('Test-Info',)}, 'Test-Info')
        ]
        for name_data, expected in test_data:
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_ausgaben_merkmal(self):
        """Check the results of get_name with ausgaben_merkmal override set."""
        name_data = {
            'ausgabejahr__jahr': ('2020',),
            'ausgabemonat__monat__abk': ('Dez',),
            'ausgabelnum__lnum': ('21',),
            'ausgabenum__num': ('20',),
            'e_datum': ('02.05.2018',),
        }
        test_data = [
            (_models.Magazin.Merkmal.E_DATUM, '02.05.2018'),
            (_models.Magazin.Merkmal.MONAT, '2020-Dez'),
            (_models.Magazin.Merkmal.NUM, '2020-20'),
            (_models.Magazin.Merkmal.LNUM, '21 (2020)'),
        ]
        for merkmal, expected in test_data:
            name_data['magazin__ausgaben_merkmal'] = (merkmal,)
            with self.subTest(merkmal=merkmal):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

        # Some edge case tests:
        # LNUM but no jahr or jahrgang:
        name_data = {
            'magazin__ausgaben_merkmal': ('lnum',),
            'ausgabelnum__lnum': ('21',)
        }
        self.assertEqual(
            self.model._get_name(**name_data), '21',
            msg="get_name should just return the lnum if ausgaben_merkmal is"
                " set to lnum and neither jahr nor jahrgang are set."
        )
        # Merkmal attribute is not set:
        name_data = {
            'magazin__ausgaben_merkmal': ('num',),
            'beschreibung': ('Whoops!',)
        }
        self.assertEqual(
            self.model._get_name(**name_data), 'Whoops!',
            msg="get_name should ignore ausgaben_merkmal if the attribute "
                "it is referring to is not set."
        )

    @translation_override(language=None)
    def test_get_name_ausgaben_merkmal_multiple_values(self):
        """Check the results of get_name with ausgaben_merkmal override set."""
        name_data = {
            'ausgabejahr__jahr': ('2021', '2020'),
            'ausgabemonat__monat__abk': ('Jan', 'Dez'),
            'ausgabelnum__lnum': ('22', '21'),
            'ausgabenum__num': ('21', '20'),
        }
        test_data = [
            (_models.Magazin.Merkmal.MONAT, '2020/21-Jan/Dez'),
            (_models.Magazin.Merkmal.NUM, '2020/21-20/21'),
            (_models.Magazin.Merkmal.LNUM, '21/22 (2020/21)'),
        ]
        for merkmal, expected in test_data:
            name_data['magazin__ausgaben_merkmal'] = (merkmal,)
            with self.subTest(merkmal=merkmal):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['magazin'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('_name', ('_name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelAusgabeJahr(MIZTestCase):
    model = _models.AusgabeJahr

    def test_str(self):
        obj = make(self.model, jahr=2018)
        self.assertEqual(str(obj), '2018')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['jahr'])


class TestModelAusgabeLnum(MIZTestCase):
    model = _models.AusgabeLnum

    def test_str(self):
        obj = make(self.model, lnum=21)
        self.assertEqual(str(obj), '21')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['lnum'])


class TestModelAusgabeMonat(MIZTestCase):
    model = _models.AusgabeMonat

    def test_str(self):
        obj = make(self.model, monat__monat='Dezember', monat__abk='Dez')
        self.assertEqual(str(obj), 'Dez')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['monat'])


class TestModelAusgabeNum(MIZTestCase):
    model = _models.AusgabeNum

    def test_str(self):
        obj = make(self.model, num=20)
        self.assertEqual(str(obj), '20')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['num'])


class TestModelMonat(MIZTestCase):
    model = _models.Monat

    def test_str(self):
        obj = self.model(monat='Dezember', abk='Dez')
        self.assertEqual(str(obj), 'Dezember')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['ordinal'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('monat', ('monat', 'A', SIMPLE)),
            ('abk', ('abk', 'A', SIMPLE)),
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelMagazin(MIZTestCase):
    model = _models.Magazin

    def test_str(self):
        obj = self.model(magazin_name='Testmagazin')
        self.assertEqual(str(obj), 'Testmagazin')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['magazin_name'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('magazin_name', ('magazin_name', 'A', SIMPLE)),
            ('issn', ('issn', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelVerlag(MIZTestCase):
    model = _models.Verlag

    def test_str(self):
        obj = self.model(verlag_name='Testverlag')
        self.assertEqual(str(obj), 'Testverlag')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['verlag_name', 'sitz'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('verlag_name', columns)
        self.assertEqual(columns['verlag_name']['name'], 'verlag_name')
        self.assertEqual(columns['verlag_name']['weight'], 'A')
        self.assertEqual(columns['verlag_name']['language'], SIMPLE)


class TestModelOrt(MIZTestCase):
    model = _models.Ort

    @translation_override(language=None)
    def test_get_name(self):
        name_data = {'land__land_name': ('Deutschland',)}
        test_data = [
            ({}, 'Deutschland'),
            ({'land__code': ('DE',), 'bland__bland_name': ('Hessen',)}, 'Hessen, DE'),
            ({'stadt': ('Kassel',)}, 'Kassel, DE'),
            ({'bland__code': ('HE',)}, 'Kassel, DE-HE')
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['land', 'bland', 'stadt'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('_name', columns)
        self.assertEqual(columns['_name']['name'], '_name')
        self.assertEqual(columns['_name']['weight'], 'A')
        self.assertEqual(columns['_name']['language'], SIMPLE)


class TestModelBundesland(MIZTestCase):
    model = _models.Bundesland

    def test_str(self):
        obj = make(self.model, bland_name='Hessen', code='HE')
        self.assertEqual(str(obj), 'Hessen HE')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['land', 'bland_name'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('bland_name', ('bland_name', 'A', SIMPLE)),
            ('code', ('code', 'A', SIMPLE)),
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelLand(MIZTestCase):
    model = _models.Land

    def test_str(self):
        obj = self.model(land_name='Deutschland', code='DE')
        self.assertEqual(str(obj), 'Deutschland DE')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['land_name'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('land_name', ('land_name', 'A', SIMPLE)),
            ('code', ('code', 'A', SIMPLE)),
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelSchlagwort(MIZTestCase):
    model = _models.Schlagwort

    def test_str(self):
        obj = self.model(schlagwort='Testschlagwort')
        self.assertEqual(str(obj), 'Testschlagwort')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['schlagwort'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('schlagwort', columns)
        self.assertEqual(columns['schlagwort']['name'], 'schlagwort')
        self.assertEqual(columns['schlagwort']['weight'], 'A')
        self.assertEqual(columns['schlagwort']['language'], SIMPLE)

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('schlagwortalias___fts', SIMPLE), self.model.related_search_vectors)


class TestModelSchlagwortAlias(MIZTestCase):
    model = _models.SchlagwortAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'A')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelArtikel(MIZTestCase):
    model = _models.Artikel
    test_data_count = 1

    def test_str(self):
        obj = make(self.model, schlagzeile="The importance of testing stuff")
        self.assertEqual(obj.__str__(), "The importance of testing stuff")
        obj.schlagzeile = ''
        self.assertEqual(obj.__str__(), 'Keine Schlagzeile gegeben!')
        obj.zusammenfassung = 'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.'
        self.assertEqual(
            obj.__str__(),
            'Dies ist eine Testzusammenfassung, die nicht besonders lang ist.'
        )

    def test_meta_ordering(self):
        """Assert that the ordering includes magazin_name and Ausgabe._name"""
        # noinspection PyUnresolvedReferences
        self.assertEqual(
            self.model._meta.ordering,
            ['ausgabe__magazin__magazin_name', 'ausgabe___name', 'seite', 'schlagzeile']
        )

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('schlagzeile', ('schlagzeile', 'A', SIMPLE)),
            ('zusammenfassung', ('zusammenfassung', 'B', STEMMING)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelBuch(MIZTestCase):
    model = _models.Buch

    def test_str(self):
        obj = make(self.model, titel="Testing With Django", seitenumfang=22, jahr=2022)
        self.assertEqual(obj.__str__(), "Testing With Django")

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelHerausgeber(MIZTestCase):
    model = _models.Herausgeber

    def test_str(self):
        obj = self.model(herausgeber='Testherausgeber')
        self.assertEqual(str(obj), 'Testherausgeber')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['herausgeber'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('herausgeber', columns)
        self.assertEqual(columns['herausgeber']['name'], 'herausgeber')
        self.assertEqual(columns['herausgeber']['weight'], 'A')
        self.assertEqual(columns['herausgeber']['language'], SIMPLE)


class TestModelInstrument(MIZTestCase):
    model = _models.Instrument

    def test_str(self):
        obj = self.model(instrument='Posaune', kuerzel='pos')
        self.assertEqual(str(obj), 'Posaune (pos)')

        obj = self.model(instrument='Posaune', kuerzel='')
        self.assertEqual(str(obj), 'Posaune')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['instrument', 'kuerzel'])

    def test_full_text_search(self):
        test_data = [
            ('instrument', ('instrument', 'A', SIMPLE)),
            ('kuerzel', ('kuerzel', 'A', SIMPLE)),
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelAudio(MIZTestCase):
    model = _models.Audio

    def test_str(self):
        obj = make(self.model, titel='Testaudio', tracks=2, beschreibung='Good soup.')
        self.assertEqual(obj.__str__(), 'Testaudio')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelPlakat(MIZTestCase):
    model = _models.Plakat

    def test_str(self):
        obj = make(self.model, titel='Testbild', size='DIN-A3')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('signatur', ('signatur', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelBildreihe(MIZTestCase):
    model = _models.Bildreihe

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('name', columns)
        self.assertEqual(columns['name']['name'], 'name')
        self.assertEqual(columns['name']['weight'], 'A')
        self.assertEqual(columns['name']['language'], SIMPLE)


class TestModelSchriftenreihe(MIZTestCase):
    model = _models.Schriftenreihe

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('name', columns)
        self.assertEqual(columns['name']['name'], 'name')
        self.assertEqual(columns['name']['weight'], 'A')
        self.assertEqual(columns['name']['language'], SIMPLE)


class TestModelDokument(MIZTestCase):
    model = _models.Dokument

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelMemorabilien(MIZTestCase):
    model = _models.Memorabilien

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelSpielort(MIZTestCase):
    model = _models.Spielort

    def test_str(self):
        land_object = _models.Land.objects.create(land_name='Deutschland', code='DE')
        obj = self.model(
            name='Testspielort', ort=_models.Ort.objects.create(land=land_object)
        )
        self.assertEqual(str(obj), 'Testspielort')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name', 'ort'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('name', ('name', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('spielortalias___fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('ort___fts', SIMPLE), self.model.related_search_vectors)


class TestModelSpielortAlias(MIZTestCase):
    model = _models.SpielortAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'A')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelTechnik(MIZTestCase):
    model = _models.Technik

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelVeranstaltung(MIZTestCase):
    model = _models.Veranstaltung

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name', 'datum', 'spielort'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('name', ('name', 'A', SIMPLE)),
            ('datum', ('datum', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('veranstaltungalias___fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('spielort___fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('spielort__ort___fts', SIMPLE), self.model.related_search_vectors)


class TestModelVeranstaltungAlias(MIZTestCase):
    model = _models.VeranstaltungAlias

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['alias'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('alias', columns)
        self.assertEqual(columns['alias']['name'], 'alias')
        self.assertEqual(columns['alias']['weight'], 'A')
        self.assertEqual(columns['alias']['language'], SIMPLE)


class TestModelVeranstaltungsreihe(MIZTestCase):
    model = _models.Veranstaltungsreihe

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('name', columns)
        self.assertEqual(columns['name']['name'], 'name')
        self.assertEqual(columns['name']['weight'], 'A')
        self.assertEqual(columns['name']['language'], SIMPLE)


class TestModelVideo(MIZTestCase):
    model = _models.Video

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelProvenienz(MIZTestCase):
    model = _models.Provenienz

    def test_str(self):
        obj = make(self.model, geber__name='TestGeber', typ=self.model.Types.FUND)
        self.assertEqual(str(obj), 'TestGeber (Fund)')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['geber', 'typ'])

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('geber___fts', SIMPLE), self.model.related_search_vectors)


class TestModelGeber(MIZTestCase):
    model = _models.Geber

    def test_str(self):
        obj = self.model(name='Testgeber')
        self.assertEqual(str(obj), 'Testgeber')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('name', columns)
        self.assertEqual(columns['name']['name'], 'name')
        self.assertEqual(columns['name']['weight'], 'A')
        self.assertEqual(columns['name']['language'], SIMPLE)


class TestModelLagerort(MIZTestCase):
    model = _models.Lagerort

    @translation_override(language=None)
    def test_get_name(self):
        name_data = {'ort': ('Testort',)}
        test_data = [
            ({}, 'Testort'),
            ({'regal': ('Testregal',)}, 'Testregal (Testort)'),
            ({'fach': ('12',)}, "Testregal-12 (Testort)")
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    @translation_override(language=None)
    def test_get_name_with_raum(self):
        name_data = {'ort': ('Testort',), 'raum': ('Testraum',)}
        test_data = [
            ({}, 'Testraum (Testort)'),
            ({'regal': ('Testregal',)}, 'Testraum-Testregal (Testort)'),
            ({'fach': ('12',)}, "Testraum-Testregal-12 (Testort)")
        ]
        for update, expected in test_data:
            name_data.update(update)
            with self.subTest(name_data=name_data):
                name = self.model._get_name(**name_data)
                self.assertEqual(name, expected)

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['_name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('_name', columns)
        self.assertEqual(columns['_name']['name'], '_name')
        self.assertEqual(columns['_name']['weight'], 'A')
        self.assertEqual(columns['_name']['language'], SIMPLE)


class TestModelBestand(MIZTestCase):
    model = _models.Bestand

    def test_str(self):
        obj = make(self.model)
        # noinspection PyUnresolvedReferences
        self.assertEqual(obj.__str__(), obj.lagerort.__str__())

    def test_bestand_object(self):
        """
        Assert that the property 'bestand_object' returns the model instance
        that the Bestand instance is meant to keep track of.
        """
        test_data = [
            ('ausgabe', _models.Ausgabe),
            ('audio', _models.Audio),
            ('brochure', _models.Katalog)
        ]
        lagerort = make(_models.Lagerort)
        for field_name, expected_model in test_data:
            with self.subTest(field_name=field_name):
                obj = _models.Bestand.objects.create(
                    **{'lagerort': lagerort, field_name: make(expected_model)}
                )
                # refresh to clear Bestand.brochure cache so that it doesn't
                # return the Katalog instance directly.
                obj.refresh_from_db()
                self.assertIsInstance(obj.bestand_object, expected_model)

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('anmerkungen', columns)
        self.assertEqual(columns['anmerkungen']['name'], 'anmerkungen')
        self.assertEqual(columns['anmerkungen']['weight'], 'A')
        self.assertEqual(columns['anmerkungen']['language'], STEMMING)


class TestModelDatei(MIZTestCase):
    model = _models.Datei

    def test_str(self):
        obj = self.model(titel='Testdatei')
        self.assertEqual(str(obj), 'Testdatei')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelPlattenfirma(MIZTestCase):
    model = _models.Plattenfirma

    def test_str(self):
        obj = self.model(name='Testfirma')
        self.assertEqual(str(obj), 'Testfirma')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['name'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('name', columns)
        self.assertEqual(columns['name']['name'], 'name')
        self.assertEqual(columns['name']['weight'], 'A')
        self.assertEqual(columns['name']['language'], SIMPLE)


class TestModelBaseBrochure(MIZTestCase):
    model = _models.BaseBrochure

    def test_str(self):
        obj = make(
            self.model, titel="Model Inheritance Is Funky",
            zusammenfassung="Alan please add a summary."
        )
        self.assertEqual(obj.__str__(), "Model Inheritance Is Funky")

    def test_resolve_child_no_children(self):
        """ resolve_child should return None, if the object has no children."""
        obj = make(self.model)
        # noinspection PyUnresolvedReferences
        self.assertIsNone(obj.resolve_child())

    def test_resolve_child(self):
        child_models = (_models.Brochure, _models.Kalender, _models.Katalog)
        for child_model in child_models:
            # noinspection PyUnresolvedReferences
            opts = child_model._meta
            with self.subTest(child_model=opts.object_name):
                obj = make(child_model)
                # Call resolve_child from the BaseBrochure parent instance.
                resolved = getattr(obj, opts.pk.name).resolve_child()
                self.assertIsInstance(resolved, child_model)

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('zusammenfassung', ('zusammenfassung', 'B', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_base_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestModelBrochure(MIZTestCase):
    model = _models.Brochure

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('beschreibung', columns)
        self.assertEqual(columns['beschreibung']['name'], 'beschreibung')
        self.assertEqual(columns['beschreibung']['weight'], 'C')
        self.assertEqual(columns['beschreibung']['language'], STEMMING)

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('basebrochure_ptr___base_fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('basebrochure_ptr___base_fts', STEMMING), self.model.related_search_vectors)


class TestModelKalender(MIZTestCase):
    model = _models.Kalender

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('beschreibung', columns)
        self.assertEqual(columns['beschreibung']['name'], 'beschreibung')
        self.assertEqual(columns['beschreibung']['weight'], 'C')
        self.assertEqual(columns['beschreibung']['language'], STEMMING)

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('basebrochure_ptr___base_fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('basebrochure_ptr___base_fts', STEMMING), self.model.related_search_vectors)


class TestModelKatalog(MIZTestCase):
    model = _models.Katalog

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_search_field_columns(self):
        """Check the columns of this model's SearchVectorField."""
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        self.assertIn('beschreibung', columns)
        self.assertEqual(columns['beschreibung']['name'], 'beschreibung')
        self.assertEqual(columns['beschreibung']['weight'], 'C')
        self.assertEqual(columns['beschreibung']['language'], STEMMING)

    def test_related_search_vectors(self):
        """Check the configs for related search vectors."""
        self.assertIn(('basebrochure_ptr___base_fts', SIMPLE), self.model.related_search_vectors)
        self.assertIn(('basebrochure_ptr___base_fts', STEMMING), self.model.related_search_vectors)


class TestModelFoto(MIZTestCase):
    model = _models.Foto

    def test_str(self):
        obj = make(self.model, titel='Testbild')
        self.assertEqual(str(obj), 'Testbild')

    def test_meta_ordering(self):
        """Check the default ordering of this model."""
        # noinspection PyUnresolvedReferences
        self.assertEqual(self.model._meta.ordering, ['titel'])

    def test_full_text_search(self):
        """Check the columns of this model's SearchVectorField."""
        test_data = [
            ('titel', ('titel', 'A', SIMPLE)),
            ('beschreibung', ('beschreibung', 'C', STEMMING)),
            ('bemerkungen', ('bemerkungen', 'D', SIMPLE))
        ]
        # noinspection PyUnresolvedReferences
        columns = get_search_field_columns(self.model._meta.get_field('_fts'))
        for column_name, expected in test_data:
            with self.subTest(column=column_name):
                self.assertIn(column_name, columns)
                column = columns[column_name]
                self.assertEqual(column['name'], expected[0])
                self.assertEqual(column['weight'], expected[1])
                self.assertEqual(column['language'], expected[2])


class TestM2mAudioMusiker(MIZTestCase):
    model = _m2m.m2m_audio_musiker

    def test_str(self):
        obj = make(
            self.model, musiker__kuenstler_name='Natalia Lafourcade',
            audio__titel='Natalia Lafourcade: NPR Music Tiny Desk Concert'
        )
        self.assertEqual(obj.__str__(), 'Natalia Lafourcade')


class TestM2mVideoMusiker(MIZTestCase):
    model = _m2m.m2m_video_musiker

    def test_str(self):
        obj = make(
            self.model, musiker__kuenstler_name='Natalia Lafourcade',
            video__titel='Natalia Lafourcade: NPR Music Tiny Desk Concert'
        )
        self.assertEqual(obj.__str__(), 'Natalia Lafourcade')


class TestM2mDateiMusiker(MIZTestCase):
    model = _m2m.m2m_datei_musiker

    def test_str(self):
        obj = make(
            self.model, musiker__kuenstler_name='Natalia Lafourcade',
            datei__titel='Natalia Lafourcade: NPR Music Tiny Desk Concert'
        )
        self.assertEqual(obj.__str__(), 'Natalia Lafourcade')
        guitar = make(_models.Instrument, instrument="Guitar", kuerzel="g")
        tambourine = make(_models.Instrument, instrument="Tambourine", kuerzel="tb")
        # noinspection PyUnresolvedReferences
        obj.instrument.add(guitar, tambourine)
        self.assertEqual(obj.__str__(), 'Natalia Lafourcade (g,tb)')
