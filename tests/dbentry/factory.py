import factory

from dbentry import models as _models
from tests.factory import MIZModelFactory, SubFactory, ISSNFaker, UniqueFaker


class AutorFactory(MIZModelFactory):
    class Meta:
        model = _models.Autor

    person = SubFactory('dbentry.factory.PersonFactory', required=True)

    # noinspection PyMethodParameters
    @factory.lazy_attribute
    def kuerzel(obj):
        """Prepare a 2 character token based on the Person's name."""
        if obj.person is None:
            return 'XY'
        # noinspection PyUnresolvedReferences
        vorname, nachname = obj.person.vorname, obj.person.nachname
        if vorname:
            return vorname[0] + nachname[0]
        return nachname[:2].upper()


class BandFactory(MIZModelFactory):
    class Meta:
        model = _models.Band
        django_get_or_create = ['band_name']

    band_name = factory.Faker('company')


class BundeslandFactory(MIZModelFactory):
    class Meta:
        model = _models.Bundesland
        django_get_or_create = ['bland_name', 'code']

    bland_name = factory.Faker('state')
    code = factory.Faker('state_abbr')


class GenreFactory(MIZModelFactory):
    class Meta:
        model = _models.Genre
        django_get_or_create = ['genre']


class LandFactory(MIZModelFactory):
    class Meta:
        model = _models.Land
        django_get_or_create = ['land_name', 'code']

    land_name = UniqueFaker('country')
    # land.code has unique=True and max_length of 4.
    # If we were to use a UniqueFaker that max_length might be exceeded
    # depending on the sequence counter (even with a faker that returns very
    # short strings such as 'country_code').
    # The end of land_name includes a unique sequence element, so just use the
    # last four chars of that name:
    code = factory.LazyAttribute(lambda o: o.land_name[-4:])


class MagazinFactory(MIZModelFactory):
    class Meta:
        model = _models.Magazin
        django_get_or_create = ['magazin_name']

    magazin_name = factory.Sequence(lambda n: 'TestMagazin' + str(n))
    issn = ISSNFaker()


class MonatFactory(MIZModelFactory):
    class Meta:
        model = _models.Monat
        django_get_or_create = ['monat', 'abk', 'ordinal']

    monat = factory.Faker('month_name')
    abk = factory.LazyAttribute(lambda o: o.monat[:3])
    ordinal = factory.Sequence(lambda n: n)


class MusikerFactory(MIZModelFactory):
    class Meta:
        model = _models.Musiker
        django_get_or_create = ['kuenstler_name']

    kuenstler_name = factory.Sequence(lambda n: 'TestMusiker' + str(n))


class OrtFactory(MIZModelFactory):
    class Meta:
        model = _models.Ort

    stadt = factory.Faker('city')


class PersonFactory(MIZModelFactory):
    class Meta:
        model = _models.Person

    vorname = factory.Faker('first_name')
    nachname = factory.Faker('last_name')


class SchlagwortFactory(MIZModelFactory):
    class Meta:
        model = _models.Schlagwort
        django_get_or_create = ['schlagwort']


# TODO: don't forget about the tests for the factories of dbentry models.
################################################################################
# TESTS?
################################################################################


# class ModelFactoryTestCase(MIZTestCase):
#
#     factory_class = None
#
#     def setUp(self):
#         super().setUp()
#         # Reset sequences:
#         if self.factory_class is not None:
#             self.factory_class.reset_sequence()
#
#
# class TestMagazinFactory(ModelFactoryTestCase):
#
#     factory_class = modelfactory_factory(_models.Magazin)
#
#     def test_magazin_name_field(self):
#         self.assertEqual(self.factory_class().magazin_name, 'TestMagazin0')
#         self.assertEqual(self.factory_class().magazin_name, 'TestMagazin1')
#         self.assertEqual(self.factory_class(__sequence=42).magazin_name, 'TestMagazin42')
#
#     def test_issn_field(self):
#         m = MagazinFactory()
#         self.assertTrue(m.issn)
#         self.assertTrue(issn.is_valid(m.issn))
#
#         m = MagazinFactory(issn='45010528')
#         self.assertEqual(m.issn, '45010528')
#
#     def test_get_or_create(self):
#         expected = self.factory_class()
#         self.assertEqual(self.factory_class(magazin_name=expected.magazin_name), expected)
#
#
# class TestAusgabeFactory(ModelFactoryTestCase):
#
#     factory_class = modelfactory_factory(_models.Ausgabe)
#
#     def test_ausgabejahr(self):
#         a = self.factory_class(ausgabejahr__jahr=2001)
#         self.assertIn(2001, a.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertEqual(a.ausgabejahr_set.count(), 1)
#
#         a = self.factory_class(ausgabejahr__jahr=[2001, 2002])
#         self.assertIn(2001, a.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertIn(2002, a.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertEqual(a.ausgabejahr_set.count(), 2)
#
#     def test_ausgabenum(self):
#         a = self.factory_class(ausgabenum__num=21)
#         self.assertIn(21, a.ausgabenum_set.values_list('num', flat=True))
#         self.assertEqual(a.ausgabenum_set.count(), 1)
#
#         a = self.factory_class(ausgabenum__num=[21, 22])
#         self.assertIn(21, a.ausgabenum_set.values_list('num', flat=True))
#         self.assertIn(22, a.ausgabenum_set.values_list('num', flat=True))
#         self.assertEqual(a.ausgabenum_set.count(), 2)
#
#     def test_ausgabelnum(self):
#         a = self.factory_class(ausgabelnum__lnum=21)
#         self.assertIn(21, a.ausgabelnum_set.values_list('lnum', flat=True))
#         self.assertEqual(a.ausgabelnum_set.count(), 1)
#
#         a = self.factory_class(ausgabelnum__lnum=[21, 22])
#         self.assertIn(21, a.ausgabelnum_set.values_list('lnum', flat=True))
#         self.assertIn(22, a.ausgabelnum_set.values_list('lnum', flat=True))
#         self.assertEqual(a.ausgabelnum_set.count(), 2)
#
#     def test_ausgabemonat(self):
#         januar, _ = _models.Monat.objects.get_or_create(
#             monat='Januar', abk='Jan', ordinal=1)
#         februar, _ = _models.Monat.objects.get_or_create(
#             monat='Februar', abk='Feb', ordinal=2)
#
#         a = self.factory_class(ausgabemonat__monat__monat='Januar')
#         self.assertIn(
#             (januar.pk, 'Januar'),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat')
#         )
#         self.assertEqual(a.ausgabemonat_set.count(), 1)
#
#         a = self.factory_class(ausgabemonat__monat__ordinal=1)
#         self.assertIn(
#             (januar.pk, 'Januar', 1),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat', 'monat__ordinal')
#         )
#         self.assertEqual(a.ausgabemonat_set.count(), 1)
#
#         a = self.factory_class(ausgabemonat__monat__monat=['Januar', 'Februar'])
#         self.assertIn(
#             (januar.pk, 'Januar'),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat')
#         )
#         self.assertIn(
#             (februar.pk, 'Februar'),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat')
#         )
#         self.assertEqual(a.ausgabemonat_set.count(), 2)
#
#         a = self.factory_class(ausgabemonat__monat__ordinal=[1, 2])
#         self.assertIn(
#             (januar.pk, 'Januar', 1),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat', 'monat__ordinal')
#         )
#         self.assertIn(
#             (februar.pk, 'Februar', 2),
#             a.ausgabemonat_set.values_list('monat__id', 'monat__monat', 'monat__ordinal')
#         )
#         self.assertEqual(a.ausgabemonat_set.count(), 2)
#
#     def test_ausgabe_magazin(self):
#         a = self.factory_class(magazin__magazin_name='Testmagazin')
#         self.assertEqual(a.magazin.magazin_name, 'Testmagazin')
#
#     def test_complex_creation(self):
#         lagerort_factory = modelfactory_factory(_models.Lagerort)
#         lagerort_1 = lagerort_factory(ort='TestLagerOrt')
#         lagerort_2 = lagerort_factory(ort='TestLagerOrt2')
#         prov = modelfactory_factory(_models.Provenienz)(geber__name='TestCase')
#
#         obj1 = self.factory_class(
#             magazin__magazin_name='Testmagazin',
#             ausgabejahr__jahr=2000, ausgabenum__num=1,
#             bestand__lagerort=lagerort_1, bestand__provenienz=prov
#         )
#         obj2 = self.factory_class(
#             magazin__magazin_name='Testmagazin',
#             ausgabejahr__jahr=2000, ausgabenum__num=2,
#             bestand__lagerort=[lagerort_1, lagerort_2],
#             bestand__provenienz=[None, prov],
#         )
#         obj3 = self.factory_class(
#             magazin__magazin_name='Testmagazin',
#             ausgabejahr__jahr=2000, ausgabenum__num=3,
#             bestand__lagerort=lagerort_2,
#         )
#
#         self.assertEqual(obj1.magazin.magazin_name, 'Testmagazin')
#         self.assertIn(2000, obj1.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertIn(1, obj1.ausgabenum_set.values_list('num', flat=True))
#         self.assertEqual(obj1.bestand_set.count(), 1)
#         self.assertEqual(obj1.bestand_set.first().lagerort, lagerort_1)
#         self.assertEqual(obj1.bestand_set.first().provenienz, prov)
#
#         self.assertEqual(obj2.magazin.magazin_name, 'Testmagazin')
#         self.assertIn(2000, obj2.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertIn(2, obj2.ausgabenum_set.values_list('num', flat=True))
#         self.assertEqual(obj2.bestand_set.count(), 2)
#         b1, b2 = obj2.bestand_set.all()
#         self.assertEqual(b1.lagerort, lagerort_1)
#         self.assertIsNone(b1.provenienz)
#         self.assertEqual(b2.lagerort, lagerort_2)
#         self.assertEqual(b2.provenienz, prov)
#
#         self.assertEqual(obj3.magazin.magazin_name, 'Testmagazin')
#         self.assertIn(2000, obj3.ausgabejahr_set.values_list('jahr', flat=True))
#         self.assertIn(3, obj3.ausgabenum_set.values_list('num', flat=True))
#         self.assertEqual(obj3.bestand_set.count(), 1)
#         self.assertEqual(obj3.bestand_set.first().lagerort, lagerort_2)
#         self.assertIsNone(obj3.bestand_set.first().provenienz)
#
#
# class TestAutorFactory(ModelFactoryTestCase):
#
#     factory_class = modelfactory_factory(_models.Autor)
#
#     def test_kuerzel_field(self):
#         # Assert that kuerzel depends on the Person's name.
#         a = self.factory_class()
#         expected = a.person.vorname[0] + a.person.nachname[0]
#         self.assertEqual(a.kuerzel, expected)
#
#         a = self.factory_class(person__vorname='', person__nachname='Foo')
#         self.assertEqual(a.kuerzel, 'FO')
#
#         a = self.factory_class(person=None)
#         self.assertEqual(a.kuerzel, 'XY')
#
#         a = self.factory_class(kuerzel='AB')
#         self.assertEqual(a.kuerzel, 'AB')
#
#
# class TestMonatFactory(ModelFactoryTestCase):
#
#     factory_class = modelfactory_factory(_models.Monat)
#
#     def test_abk_field(self):
#         # Assert that abk depends on the monat's 'name'.
#         m = self.factory_class()
#         self.assertEqual(m.abk, m.monat[:3])
#
#         m = self.factory_class(monat='Nope')
#         self.assertEqual(m.abk, 'Nop')
#
#     def test_get_or_create(self):
#         expected = self.factory_class()
#         self.assertEqual(self.factory_class(monat=expected.monat), expected)
#
#