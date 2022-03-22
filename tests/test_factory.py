from unittest import mock

from stdnum import issn
from unittest.mock import Mock, patch

from django.apps import apps
from django.db import models

# import dbentry.models as _models
# from dbentry.base.models import BaseModel, BaseM2MModel
from tests.factory import (
    factory, RuntimeFactoryMixin, RelatedFactory, UniqueFaker, modelfactory_factory, make,
    SelfFactory, MIZDjangoOptions
)
from tests.case import MIZTestCase
from tests.models import Ancestor, Ausgabe, Magazin
from dbentry.utils import get_model_relations, get_model_fields


class DummyModel(models.Model):
    pass


class DummyModelFactory(object):  # need not be an actual factory type
    pass


class AncestorFactory(factory.Factory):
    class Meta:
        model = Ancestor
    name = factory.Faker('word')
    ancestor = SelfFactory('tests.test_factory.AncestorFactory', required=False)

    @classmethod
    def set_memo(cls, *args, **kwargs):
        # Fake MIZModelFactory's set_memo.
        pass


class MagazinFactory(factory.Factory):
    class Meta:
        model = Magazin

    magazin_name = factory.Faker('word')
    ausgaben = RelatedFactory(
        'tests.test_factory.AusgabeFactory',
        factory_related_name='magazin',
        accessor_name='ausgaben',
        related_model=Ausgabe,
    )


class AusgabeFactory(factory.Factory):
    class Meta:
        model = Ausgabe

    name = factory.Faker('word')
    magazin = factory.SubFactory('tests.test_factory.MagazinFactory')


class TestRuntimeFactoryMixin(MIZTestCase):
    class SubFactory(RuntimeFactoryMixin, factory.SubFactory):
        pass

    def test_existing_factory(self):
        """
        Assert that the factory property returns the factory we're passing to
        mixin's __init__.
        """
        fac = self.SubFactory(DummyModelFactory)
        self.assertEqual(DummyModelFactory, fac.factory)

    def test_new_factory(self):
        """Assert that the factory property can create a new factory if needed."""
        fac = self.SubFactory(self.__module__ + '.DoesNotExit', related_model=DummyModel)
        m = mock.Mock(return_value=DummyModelFactory)
        with patch('tests.factory.modelfactory_factory', new=m):
            self.assertEqual(fac.factory, DummyModelFactory)
            m.assert_called_with(DummyModel)

    def test_new_factory_without_related_model(self):
        """
        factory property should raise an AttributeError, if the factory's
        related_model attribute is None and a new factory has to be created.
        """
        fac = self.SubFactory(self.__module__ + 'beep', related_model=None)
        with self.assertRaises(AttributeError):
            fac.factory  # noqa


class TestUniqueFaker(MIZTestCase):

    def test_init_no_function(self):
        """
        UniqueFaker.function should default to a function 'default_callable'
        that simply returns the input.
        """
        faker = UniqueFaker('name', function=None)
        self.assertEqual(faker.function.__name__, 'default_callable')
        self.assertEqual(faker.function(1), 1)
        self.assertEqual(faker.function(42), 42)

    def test_init(self):
        """
        UniqueFaker should accept a provider's name as well as a factory.Faker
        instance.
        """
        faker = UniqueFaker('month')
        self.assertEqual(faker.faker.provider, 'month')

        faker = UniqueFaker(factory.Faker('month'), function=lambda n: n)
        self.assertEqual(faker.faker.provider, 'month')


class TestSelfFactory(MIZTestCase):

    def test_evaluate(self):
        fac = AncestorFactory
        created = fac(ancestor=None)
        self.assertIsNone(created.ancestor)

        created = fac(ancestor__ancestor__ancestor=None)
        self.assertIsNotNone(created.ancestor)
        self.assertIsNotNone(created.ancestor.ancestor)
        self.assertIsNone(created.ancestor.ancestor.ancestor)

        # No Ancestor should be created:
        created = fac()
        self.assertIsNone(created.ancestor)

        # And now with actual data:
        mother = fac(name='Alice')
        mother.save()
        son = fac(name='Bob', ancestor=mother)
        son.save()
        self.assertEqual(son.ancestor, mother)
        self.assertIn(son, mother.children.all())

        # Assert that SelfFactory creates one related object if it is required.
        fac.ancestor.required = True
        created = fac()
        self.assertIsNotNone(created.ancestor)
        self.assertIsNone(created.ancestor.ancestor)


class TestRelatedFactory(MIZTestCase):

    def test_rf_string_direct(self):
        """RelatedFactory should be able to handle string values."""
        m = MagazinFactory(ausgaben__name='Heft Eins')
        m.save()
        self.assertIn('Heft Eins', m.ausgaben.values_list('name', flat=True))

    def test_rf_string_item_list(self):
        """RelatedFactory should be able to handle single item lists."""
        m = MagazinFactory(ausgaben__name=['Heft Eins'])
        m.save()
        self.assertIn('Heft Eins', m.ausgaben.values_list('name', flat=True))

    def test_rf_list(self):
        """RelatedFactory should be able to handle lists."""
        m = MagazinFactory(ausgaben__name=['Heft Eins', 'Heft Zwei'])
        m.save()
        self.assertIn('Heft Eins', m.ausgaben.values_list('name', flat=True))
        self.assertIn('Heft Zwei', m.ausgaben.values_list('name', flat=True))

    def test_rf_instance_direct(self):
        """RelatedFactory should be able to handle model instances."""
        a = AusgabeFactory()
        a.save()
        m = MagazinFactory(ausgaben=a)
        m.save()
        self.assertIn(a, m.ausgaben.all())

    def test_rf_instance_single_list(self):
        """RelatedFactory should be able to a list of one model instance."""
        a = AusgabeFactory()
        a.save()
        m = MagazinFactory(ausgaben=[a])
        m.save()
        self.assertIn(a, m.ausgaben.all())

    def test_rf_instance_list(self):
        """RelatedFactory should be able to a list of model instances."""
        a1 = AusgabeFactory()
        a1.save()
        a2 = AusgabeFactory()
        a2.save()
        m = MagazinFactory(ausgaben=[a1, a2])
        m.save()
        self.assertIn(a1, m.ausgaben.all())
        self.assertIn(a2, m.ausgaben.all())

    def test_rf_extra(self):
        """
        RelatedFactory should create additional related instances according to
        the 'extra' keyword.
        """
        # FIXME: MagazinFactory doesn't save the created instance
        #  it just *builds* the instance.
        m = MagazinFactory.create(ausgaben__extra=3)
        self.assertEqual(m.ausgaben.count(), 3)


# class TestM2MFactory(MIZTestCase):
#
#     def test_m2m_string_direct(self):
#         m = make(_models.Musiker, genre__genre='TestGenre1')
#         self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
#
#     def test_m2m_string_single_list(self):
#         m = make(_models.Musiker, genre__genre=['TestGenre1'])
#         self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
#
#     def test_m2m_string_list(self):
#         m = make(_models.Musiker, genre__genre=['TestGenre1', 'TestGenre2'])
#         self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
#         self.assertIn('TestGenre2', m.genre.values_list('genre', flat=True))
#
#     def test_m2m_instance_direct(self):
#         g1 = make(_models.Genre)
#         m = make(_models.Musiker, genre=g1)
#         self.assertIn(g1, m.genre.all())
#
#     def test_m2m_instance_single_list(self):
#         g1 = make(_models.Genre)
#         m = make(_models.Musiker, genre=[g1])
#         self.assertIn(g1, m.genre.all())
#
#     def test_m2m_instance_list(self):
#         g1 = make(_models.Genre)
#         g2 = make(_models.Genre)
#         m = make(_models.Musiker, genre=[g1, g2])
#         self.assertIn(g1, m.genre.all())
#         self.assertIn(g2, m.genre.all())
#
#     def test_m2m_extra(self):
#         m = make(_models.Musiker, genre__extra=3)
#         self.assertEqual(m.genre.count(), 3)
#
#         g1 = make(_models.Genre)
#         g2 = make(_models.Genre)
#         m = make(_models.Musiker, genre=[g1, g2], genre__extra=2)
#         self.assertIn(g1, m.genre.all())
#         self.assertIn(g2, m.genre.all())
#         self.assertEqual(m.genre.count(), 4)
#
#
# class TestMIZDjangoOptions(MIZTestCase):
#
#     def test_get_decl_for_model_field(self):
#         # Assert that the dynamically added 'base' fields have the correct types.
#         func = MIZDjangoOptions._get_decl_for_model_field
#         # CharField / TextField => factory.Faker('word') || UniqueFaker('word') if unique
#         decl = func(models.CharField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'word')
#         decl = func(models.TextField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'word')
#
#         decl = func(models.CharField(unique=True))
#         self.assertIsInstance(decl, UniqueFaker)
#         self.assertEqual(decl.faker.provider, 'word')
#         decl = func(models.TextField(unique=True))
#         self.assertIsInstance(decl, UniqueFaker)
#         self.assertEqual(decl.faker.provider, 'word')
#
#         # IntegerField => factory.Faker('pyint') || factory.Sequence(lambda n: n) if unique
#         decl = func(models.IntegerField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'pyint')
#
#         decl = func(models.IntegerField(unique=True))
#         self.assertIsInstance(decl, factory.Sequence)
#
#         # BooleanField =>  factory.Faker('pybool')
#         decl = func(models.BooleanField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'pybool')
#
#         # DateField => factory.Faker('date')
#         decl = func(models.DateField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'date')
#
#         decl = func(models.DateTimeField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'date_time')
#
#         decl = func(models.TimeField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'time')
#
#         # DurationField => factory.Faker('time_delta')
#         decl = func(models.DurationField())
#         self.assertIsInstance(decl, factory.Faker)
#         self.assertEqual(decl.provider, 'time_delta')
#
#     def test_get_decl_for_model_field_no_declaration(self):
#         # Assert that _get_decl_for_model_field raises an Exception if no faker
#         # declaration could be assigned to the given model field.
#         mocked_field = Mock()
#         mocked_field.get_internal_type.return_value = 'EGG & SPAM'
#         with self.assertRaises(Exception):
#             MIZDjangoOptions._get_decl_for_model_field(mocked_field)
#
#     def test_adds_required_fields(self):
#         # A dynamically created factory *must* include model fields that are required.
#         # Model veranstaltung has three required fields:
#         # name (CharField), datum (DateField), spielort (ForeignKey(spielort))
#         fac = modelfactory_factory(_models.Veranstaltung)
#         self.assertIn('name', dir(fac))
#         self.assertIn('datum', dir(fac))
#         self.assertIn('spielort', dir(fac))
#
#     def test_add_m2m_factories(self):
#         # Assert that the created m2m factories are following the relation correctly.
#         fac = modelfactory_factory(_models.Artikel)
#         self.assertEqual(fac.genre.factory._meta.model, _models.Genre)
#         self.assertEqual(fac.schlagwort.factory._meta.model, _models.Schlagwort)
#         self.assertEqual(fac.person.factory._meta.model, _models.Person)
#         self.assertEqual(fac.autor.factory._meta.model, _models.Autor)
#         self.assertEqual(fac.band.factory._meta.model, _models.Band)
#         self.assertEqual(fac.musiker.factory._meta.model, _models.Musiker)
#         self.assertEqual(fac.ort.factory._meta.model, _models.Ort)
#         self.assertEqual(fac.spielort.factory._meta.model, _models.Spielort)
#         self.assertEqual(fac.veranstaltung.factory._meta.model, _models.Veranstaltung)
#
#         fac = modelfactory_factory(_models.Musiker)
#         self.assertEqual(fac.audio.factory._meta.model, _models.Audio)
#         self.assertEqual(fac.orte.factory._meta.model, _models.Ort)
#         self.assertEqual(fac.artikel.factory._meta.model, _models.Artikel)
#         self.assertEqual(fac.memorabilien.factory._meta.model, _models.Memorabilien)
#         self.assertEqual(fac.datei.factory._meta.model, _models.Datei)
#         self.assertEqual(fac.technik.factory._meta.model, _models.Technik)
#         self.assertEqual(fac.plakat.factory._meta.model, _models.Plakat)
#         self.assertEqual(fac.video.factory._meta.model, _models.Video)
#         self.assertEqual(fac.dokument.factory._meta.model, _models.Dokument)
#         self.assertEqual(fac.veranstaltung.factory._meta.model, _models.Veranstaltung)
#         self.assertEqual(fac.genre.factory._meta.model, _models.Genre)
#         self.assertEqual(fac.buch.factory._meta.model, _models.Buch)
#         self.assertEqual(fac.instrument.factory._meta.model, _models.Instrument)
#         self.assertEqual(fac.band.factory._meta.model, _models.Band)
#
#     @staticmethod
#     def get_mocked_field(field_name, model, related_model):
#         mocked_field = Mock(model=model, related_model=related_model)
#         mocked_field.configure_mock(name=field_name)
#         return mocked_field
#
#     @staticmethod
#     def get_mocked_rel(rel_name, accessor_name, **kwargs):
#         mocked_rel = Mock(get_accessor_name=Mock(return_value=accessor_name), **kwargs)
#         mocked_rel.configure_mock(name=rel_name)
#         return mocked_rel
#
#     @patch('dbentry.factory.get_model_relations')
#     def test_add_m2m_factories_inherited_relation(self, mocked_get_model_relations):
#         # Assert that add_m2m_factories can handle inherited ManyToManyRelations.
#         # Pretend factory has no attributes, so add_m2m_factories will try to add one:
#         mocked_factory = Mock(spec=[])
#
#         # Relation from BaseBrochure to genre inherited by Kalender; expected:
#         # declaration name and descriptor_name = 'mocked_field_name'
#         # related_model = _models.Genre
#         mocked_rel = self.get_mocked_rel(
#             'mocked_rel_name', 'mocked_rel_accessor',
#             field=self.get_mocked_field(
#                 'mocked_field_name', model=_models.BaseBrochure, related_model=_models.Genre)
#         )
#         mocked_get_model_relations.return_value = [mocked_rel]
#         opts = MIZDjangoOptions()
#         opts.factory = mocked_factory
#         opts.model = _models.Kalender
#         mocked_factory_name = Mock(return_value='SomeFactory')
#         with patch.object(opts, '_get_factory_name_for_model', new=mocked_factory_name):
#             with patch('dbentry.factory.M2MFactory') as mocked_m2m_factory:
#                 opts.add_m2m_factories()
#
#         self.assertTrue(hasattr(opts.factory, 'mocked_field_name'))
#         self.assertIsInstance(opts.factory.mocked_field_name, Mock)
#         expected_kwargs = {
#             'factory': 'SomeFactory',
#             'descriptor_name': 'mocked_field_name',
#             'related_model': _models.Genre
#         }
#         self.assertEqual(mocked_m2m_factory.call_args, ((), expected_kwargs))
#
#         # Relation from genre to BaseBrochure inherited by Kalender; expected:
#         # declaration name = 'mocked_rel_name';
#         # descriptor_name = 'mocked_rel_accessor';
#         # related_model = _models.Genre
#         mocked_rel = self.get_mocked_rel(
#             'mocked_rel_name', 'mocked_rel_accessor',
#             field=self.get_mocked_field(
#                 'mocked_field_name', model=_models.Genre, related_model=_models.BaseBrochure)
#         )
#         mocked_get_model_relations.return_value = [mocked_rel]
#         opts = MIZDjangoOptions()
#         opts.factory = mocked_factory
#         opts.model = _models.Kalender
#         mocked_factory_name = Mock(return_value='SomeFactory')
#         with patch.object(opts, '_get_factory_name_for_model', new=mocked_factory_name):
#             with patch('dbentry.factory.M2MFactory') as mocked_m2m_factory:
#                 opts.add_m2m_factories()
#
#         self.assertTrue(hasattr(opts.factory, 'mocked_rel_name'))
#         self.assertIsInstance(opts.factory.mocked_rel_name, Mock)
#         expected_kwargs = {
#             'factory': 'SomeFactory',
#             'descriptor_name': 'mocked_rel_accessor',
#             'related_model': _models.Genre
#         }
#         self.assertEqual(mocked_m2m_factory.call_args, ((), expected_kwargs))
#
#     @patch('dbentry.factory.get_model_relations')
#     def test_add_m2m_factories_unknown_relation(self, mocked_get_model_relations):
#         # Assert that add_m2m_factories raises a TypeError if it encounters a relation that:
#         # - does not originate from self.model
#         # - does not target self.model
#         # - is not an inherited relation
#         mocked_rel = self.get_mocked_rel(
#             'mocked_rel_name', 'mocked_rel_accessor',
#             field=self.get_mocked_field(
#                 'mocked_field_name', model=_models.Ort, related_model=_models.Instrument),
#             many_to_many=True,
#         )
#         mocked_get_model_relations.return_value = [mocked_rel]
#         opts = MIZDjangoOptions()
#         opts.model = _models.Buch
#         with self.assertRaises(TypeError):
#             opts.add_m2m_factories()
#
#     def test_add_related_factories(self):
#         # Assert that the created related factories are following the relation correctly.
#         fac = modelfactory_factory(_models.Buch)
#         self.assertEqual(fac.schriftenreihe.factory._meta.model, _models.Schriftenreihe)
#         self.assertEqual(fac.buchband.factory._meta.model, _models.Buch)
#         self.assertEqual(fac.verlag.factory._meta.model, _models.Verlag)
#
#     @patch('dbentry.factory.get_model_relations')
#     def test_add_related_factories_inherited_relation(self, mocked_get_model_relations):
#         # Assert that add_related_factories can handle inherited relations.
#         # Pretend factory has no attributes, so add_related_factories will try to add one:
#         mocked_factory = Mock(spec=[])
#         mocked_rel = self.get_mocked_rel(
#             'mocked_rel_name', 'mocked_rel_accessor',
#             field=self.get_mocked_field(
#                 'mocked_field_name', model=_models.BaseBrochure, related_model=_models.Genre),
#             many_to_many=False, model=_models.Genre, related_model=_models.BaseBrochure
#         )
#         mocked_get_model_relations.return_value = [mocked_rel]
#
#         opts = MIZDjangoOptions()
#         opts.factory = mocked_factory
#         opts.model = _models.Kalender
#         mocked_factory_name = Mock(return_value='SomeFactory')
#         with patch.object(opts, '_get_factory_name_for_model', new=mocked_factory_name):
#             with patch('dbentry.factory.RelatedFactory') as mocked_related_factory:
#                 opts.add_related_factories()
#
#                 self.assertTrue(hasattr(opts.factory, 'mocked_rel_name'))
#                 self.assertIsInstance(opts.factory.mocked_rel_name, Mock)
#                 expected_kwargs = {
#                     'factory': 'SomeFactory',
#                     'factory_related_name': 'mocked_field_name',
#                     'accessor_name': 'mocked_rel_accessor',
#                     'related_model': _models.BaseBrochure
#                 }
#                 self.assertEqual(
#                     mocked_related_factory.call_args, ((), expected_kwargs))
#
#     def test_add_sub_factories(self):
#         # Assert that self relations are recognized properly
#         fac = modelfactory_factory(_models.Buch)
#         self.assertIsInstance(fac.buchband, SelfFactory)
#
#     def test_check_declarations(self):
#         # Assert that all dynamically created factories are accounted for
#         # in the correct declaration sets.
#         buch = _models.Buch
#         fac = modelfactory_factory(buch)
#         declarations = fac._meta.declarations
#         # required base fields
#         for field in get_model_fields(buch, foreign=False, m2m=False):
#             if field.has_default() or field.blank:
#                 continue
#             self.assertIn(
#                 field.name, declarations,
#                 msg='{} not found in base declarations'.format(field.name)
#             )
#         self.assertIn('titel', declarations)
#
#         # SubFactories
#         for field in get_model_fields(buch, base=False, foreign=True, m2m=False):
#             self.assertIn(
#                 field.name, declarations,
#                 msg='{} not found in SubFactory declarations'.format(field.name)
#             )
#         self.assertIn('verlag', declarations)
#
#         # RelatedFactories
#         for rel in get_model_relations(buch, forward=False):
#             if rel.many_to_many:
#                 continue
#             name = rel.name
#             self.assertIn(
#                 name, declarations,
#                 msg='{} not found in reverse related declarations'.format(name)
#             )
#         self.assertIn('bestand', declarations)
#
#         # M2MFactories
#         for rel in get_model_relations(buch):
#             if not rel.many_to_many:
#                 continue
#             if rel.field.model == buch:
#                 name = rel.field.name
#             else:
#                 name = rel.name
#             self.assertIn(
#                 name, declarations,
#                 msg='{} not found in M2MFactory declarations'.format(name)
#             )
#         self.assertIn('genre', declarations)
#         self.assertIn('musiker', declarations)
#         self.assertIn('schlagwort', declarations)
#         self.assertIn('spielort', declarations)
#         self.assertIn('person', declarations)
#         self.assertIn('band', declarations)
#         self.assertIn('veranstaltung', declarations)
#
#
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
# class TestMIZModelFactory(MIZTestCase):
#
#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()
#         cls.factories = []
#         models = [
#             m
#             for m in apps.get_models('dbentry')
#             if issubclass(m, BaseModel) and not issubclass(m, (BaseM2MModel, _models.BaseBrochure))
#         ]
#         for model in models:
#             cls.factories.append(modelfactory_factory(model))
#
#     def assertAllRelationsUsed(self, obj):
#         for rel in get_model_relations(obj._meta.model):
#             if rel.many_to_many:
#                 if rel.related_model == obj._meta.model:
#                     # field is declared on obj
#                     self.assertTrue(getattr(obj, rel.field.name).all().exists(), msg=rel.name)
#                 elif rel.model == obj._meta.model:
#                     self.assertTrue(
#                         getattr(obj, rel.get_accessor_name()).all().exists(),
#                         msg=rel.name
#                     )
#             elif rel.model == obj._meta.model:
#                 # reverse foreign to obj
#                 self.assertTrue(
#                     getattr(obj, rel.get_accessor_name()).all().exists(),
#                     msg=rel.name
#                 )
#             else:
#                 self.assertTrue(getattr(obj, rel.field.name), msg=rel.name)
#
#     def test_full_relations(self):
#         for fac in self.factories:
#             obj = fac.full_relations()
#             with self.subTest(factory=str(fac)):
#                 self.assertAllRelationsUsed(obj)
