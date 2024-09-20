from unittest import mock
from unittest.mock import Mock, patch

from django.db import models
from stdnum import issn

from dbentry import models as _models
from tests.case import MIZTestCase
from tests.model_factory import (
    M2MFactory,
    MIZDjangoOptions,
    RelatedFactory,
    RuntimeFactoryMixin,
    SelfFactory,
    UniqueFaker,
    factory,
    modelfactory_factory,
)

from .models import Ancestor, Audio, Ausgabe, Band, Bestand, Magazin


class AncestorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ancestor

    name = factory.Faker("word")
    ancestor = SelfFactory("tests.test_factory.test.AncestorFactory", required=False)

    @classmethod
    def set_memo(cls, *args, **kwargs):
        # Fake MIZModelFactory's set_memo.
        pass


class MagazinFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Magazin

    magazin_name = factory.Faker("word")
    ausgaben = RelatedFactory(
        "tests.test_factory.test.AusgabeFactory",
        factory_related_name="magazin",
        accessor_name="ausgaben",
        related_model=Ausgabe,
    )


class AusgabeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ausgabe

    name = factory.Faker("word")
    magazin = factory.SubFactory("tests.test_factory.test.MagazinFactory")


class BandFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Band

    band_name = factory.Faker("word")


class AudioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Audio

    titel = factory.Faker("word")
    band = M2MFactory("tests.test_factory.test.BandFactory", descriptor_name="band")


class TestRuntimeFactoryMixin(MIZTestCase):
    class SubFactory(RuntimeFactoryMixin, factory.SubFactory):
        pass

    def test_existing_factory(self):
        """
        Assert that the factory property returns the factory we're passing to
        mixin's __init__.
        """

        class DummyModelFactory(object):
            pass

        fac = self.SubFactory(DummyModelFactory)
        self.assertEqual(fac.factory, DummyModelFactory)

    def test_new_factory(self):
        """Assert that the factory property can create a new factory if needed."""

        class DummyModel(models.Model):
            pass

        class DummyModelFactory(object):
            pass

        fac = self.SubFactory(self.__module__ + ".DoesNotExit", related_model=DummyModel)
        m = mock.Mock(return_value=DummyModelFactory)
        with patch("tests.model_factory.modelfactory_factory", new=m):
            self.assertEqual(fac.factory, DummyModelFactory)
            m.assert_called_with(DummyModel)

    def test_new_factory_without_related_model(self):
        """
        factory property should raise an AttributeError, if the factory's
        related_model attribute is None and a new factory has to be created.
        """
        fac = self.SubFactory(self.__module__ + "beep", related_model=None)
        with self.assertRaises(AttributeError):
            fac.factory  # noqa


class TestUniqueFaker(MIZTestCase):
    def test_init_no_function(self):
        """
        UniqueFaker.function should default to a function 'default_callable'
        that simply returns the input.
        """
        faker = UniqueFaker("name", function=None)
        self.assertEqual(faker.function.__name__, "default_callable")
        self.assertEqual(faker.function(1), 1)
        self.assertEqual(faker.function(42), 42)

    def test_init(self):
        """
        UniqueFaker should accept a provider's name as well as a factory.Faker
        instance.
        """
        faker = UniqueFaker("month")
        self.assertEqual(faker.faker.provider, "month")

        faker = UniqueFaker(factory.Faker("month"), function=lambda n: n)
        self.assertEqual(faker.faker.provider, "month")

    def test_evaluate(self):
        """
        UniqueFaker.evaluate should return a string with a sequence number
        ('step.sequence') added on to the end.
        """

        class BuildStep:
            sequence = None

        faker = UniqueFaker("word")
        step = BuildStep()
        step.sequence = 42
        self.assertTrue(faker.evaluate(None, step, {}).endswith("42"))


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
        mother = fac(name="Alice")
        son = fac(name="Bob", ancestor=mother)
        self.assertEqual(son.ancestor, mother)
        self.assertIn(son, mother.children.all())

        # Assert that SelfFactory creates one related object if it is required.
        fac.ancestor.required = True
        created = fac()
        self.assertIsNotNone(created.ancestor)
        self.assertIsNone(created.ancestor.ancestor)


class TestRelatedFactory(MIZTestCase):
    def test_rf_string_direct(self):
        """RelatedFactory should be able to handle string parameters."""
        m = MagazinFactory(ausgaben__name="Heft Eins")
        self.assertIn("Heft Eins", m.ausgaben.values_list("name", flat=True))

    def test_rf_string_item_list(self):
        """RelatedFactory should be able to handle single-item list parameters."""
        m = MagazinFactory(ausgaben__name=["Heft Eins"])
        self.assertIn("Heft Eins", m.ausgaben.values_list("name", flat=True))

    def test_rf_list(self):
        """RelatedFactory should be able to handle lists of string parameters."""
        m = MagazinFactory(ausgaben__name=["Heft Eins", "Heft Zwei"])
        self.assertIn("Heft Eins", m.ausgaben.values_list("name", flat=True))
        self.assertIn("Heft Zwei", m.ausgaben.values_list("name", flat=True))

    def test_rf_instance_direct(self):
        """RelatedFactory should be able to handle a model instance parameter."""
        a = AusgabeFactory()
        m = MagazinFactory(ausgaben=a)
        self.assertIn(a, m.ausgaben.all())

    def test_rf_instance_single_list(self):
        """
        RelatedFactory should be able to handle a single model instance list
        parameter.
        """
        a = AusgabeFactory()
        m = MagazinFactory(ausgaben=[a])
        self.assertIn(a, m.ausgaben.all())

    def test_rf_instance_list(self):
        """
        RelatedFactory should be able to handle lists of model instance
        parameters.
        """
        a1 = AusgabeFactory()
        a2 = AusgabeFactory()
        m = MagazinFactory(ausgaben=[a1, a2])
        self.assertIn(a1, m.ausgaben.all())
        self.assertIn(a2, m.ausgaben.all())

    def test_rf_extra(self):
        """
        RelatedFactory should create additional related instances according to
        the 'extra' keyword.
        """
        m = MagazinFactory.create(ausgaben__extra=3)
        self.assertEqual(m.ausgaben.count(), 3)


class TestM2MFactory(MIZTestCase):
    def test_m2m_string_direct(self):
        """M2MFactory should be able to handle string parameters."""
        a = AudioFactory(band__band_name="Tool")
        self.assertIn("Tool", a.band.values_list("band_name", flat=True))

    def test_m2m_string_single_list(self):
        """M2MFactory should be able to handle single-item list parameters."""
        a = AudioFactory(band__band_name=["Tool"])
        self.assertIn("Tool", a.band.values_list("band_name", flat=True))

    def test_m2m_string_list(self):
        """M2MFactory should be able to handle lists of string parameters."""
        a = AudioFactory(band__band_name=["Tool", "Led Zeppelin"])
        self.assertIn("Tool", a.band.values_list("band_name", flat=True))
        self.assertIn("Led Zeppelin", a.band.values_list("band_name", flat=True))

    def test_m2m_instance_direct(self):
        """M2MFactory should be able to handle a model instance parameter."""
        b = BandFactory()
        a = AudioFactory(band=b)
        self.assertIn(b, a.band.all())

    def test_m2m_instance_single_list(self):
        """
        M2MFactory should be able to handle a single model instance list
        parameter.
        """
        b = BandFactory()
        a = AudioFactory(band=[b])
        self.assertIn(b, a.band.all())

    def test_m2m_instance_list(self):
        """M2MFactory should be able to handle lists of model instance parameters."""
        b1 = BandFactory()
        b2 = BandFactory()
        a = AudioFactory(band=[b1, b2])
        self.assertIn(b1, a.band.all())
        self.assertIn(b2, a.band.all())

    def test_m2m_extra(self):
        """
        M2MFactory should create additional related instances according to the
        'extra' keyword.
        """
        a = AudioFactory(band__extra=3)
        self.assertEqual(a.band.count(), 3)

        b1 = BandFactory()
        b2 = BandFactory()
        a = AudioFactory(band=[b1, b2], band__extra=2)
        self.assertIn(b1, a.band.all())
        self.assertIn(b2, a.band.all())
        self.assertEqual(a.band.count(), 4)


class TestMIZDjangoOptions(MIZTestCase):
    def test_get_decl_for_model_field(self):
        """
        Assert that for a given model field, _get_decl_for_model_field returns
        the expected factory faker declarations.
        """
        func = MIZDjangoOptions._get_decl_for_model_field

        # CharField / TextField => factory.Faker('word')
        # or: UniqueFaker('word') if unique
        decl = func(models.CharField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "word")
        decl = func(models.TextField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "word")

        decl = func(models.CharField(unique=True))
        self.assertIsInstance(decl, UniqueFaker)
        self.assertEqual(decl.faker.provider, "word")
        decl = func(models.TextField(unique=True))
        self.assertIsInstance(decl, UniqueFaker)
        self.assertEqual(decl.faker.provider, "word")

        # IntegerField => factory.Faker('pyint')
        # or: factory.Sequence(lambda n: n) if unique
        decl = func(models.IntegerField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "pyint")

        decl = func(models.IntegerField(unique=True))
        self.assertIsInstance(decl, factory.Sequence)

        # BooleanField =>  factory.Faker('pybool')
        decl = func(models.BooleanField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "pybool")

        # DateField => factory.Faker('date')
        decl = func(models.DateField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "date")

        decl = func(models.DateTimeField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "date_time")

        decl = func(models.TimeField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "time")

        # DurationField => factory.Faker('time_delta')
        decl = func(models.DurationField())
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, "time_delta")

    def test_get_decl_for_model_field_no_declaration(self):
        """
        Assert that _get_decl_for_model_field raises an exception, if no faker
        declaration could be assigned to the given model field.
        """
        mocked_field = Mock()
        mocked_field.get_internal_type.return_value = "EGG & SPAM"
        with self.assertRaises(Exception):
            MIZDjangoOptions._get_decl_for_model_field(mocked_field)

    def test_adds_required_fields(self):
        """Assert that add_base_fields adds declarations for required fields."""
        opts = MIZDjangoOptions()
        opts.factory = type("DummyFactory", (object,), {})
        opts.model = Audio
        fields = [
            Audio._meta.get_field("titel"),
            Audio._meta.get_field("tracks"),
            Audio._meta.get_field("beschreibung"),
        ]
        with mock.patch("tests.model_factory.get_model_fields", Mock(return_value=fields)):
            opts.add_base_fields()
        # 'titel' is required, 'tracks' has default value, and 'beschreibung'
        # is not required (blank=True)
        self.assertIn("titel", dir(opts.factory))
        self.assertNotIn("tracks", dir(opts.factory))
        self.assertNotIn("beschreibung", dir(opts.factory))

    def test_add_m2m_factories(self):
        """Assert that add_m2m_factories adds declarations for M2M relations."""
        opts = MIZDjangoOptions()

        # 'forward': Audio has ManyToManyField to Band
        opts.model = Audio
        opts.factory = type("DummyFactory", (object,), {})
        rel = Audio._meta.get_field("band").remote_field
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            opts.add_m2m_factories()
        self.assertTrue(hasattr(opts.factory, "band"))
        self.assertEqual(getattr(opts.factory, "band").related_model, Band)

        # 'reverse': Band to Audio
        opts.model = Band
        opts.factory = type("DummyFactory", (object,), {})
        rel = Band._meta.get_field("audio")
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            opts.add_m2m_factories()
        self.assertTrue(hasattr(opts.factory, "audio"))
        self.assertEqual(getattr(opts.factory, "audio").related_model, Audio)

    def test_add_m2m_factories_inherited_relation(self):
        """Assert that add_m2m_factories can handle inherited ManyToManyRelations."""

        class Fan(models.Model):
            clubs = models.ManyToManyField("BaseClub", related_name="fans")

        class Player(models.Model):
            pass

        class BaseClub(models.Model):
            players = models.ManyToManyField("Player", related_name="clubs")

        class Club(BaseClub):
            pass

        opts = MIZDjangoOptions()
        opts.model = Club

        opts.factory = type("ClubFactory", (object,), {})
        # Relation from BaseClub to Players inherited by Club;
        # (rel.field.model is in Club._meta.parents)
        rel = BaseClub._meta.get_field("players").remote_field
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            opts.add_m2m_factories()
        self.assertTrue(hasattr(opts.factory, "players"))
        self.assertEqual(getattr(opts.factory, "players").descriptor_name, "players")
        self.assertEqual(getattr(opts.factory, "players").related_model, Player)

        opts.factory = type("ClubFactory", (object,), {})
        # Relation from Fans to BaseClub inherited by Club;
        # (rel.field.related_model is in Club._meta.parents)
        rel = Fan._meta.get_field("clubs").remote_field
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            opts.add_m2m_factories()
        self.assertTrue(hasattr(opts.factory, "fans"))
        self.assertEqual(getattr(opts.factory, "fans").descriptor_name, "fans")
        self.assertEqual(getattr(opts.factory, "fans").related_model, Fan)

    def test_add_m2m_factories_unknown_relation(self):
        """
        Assert that add_m2m_factories raises a TypeError, if it encounters a
        relation that isn't related to the model.
        """
        opts = MIZDjangoOptions()
        opts.model = Band
        rel = Audio._meta.get_field("genre").remote_field
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            with self.assertRaises(TypeError):
                opts.add_m2m_factories()

    def test_add_related_factories(self):
        """
        Assert that add_related_factories adds declarations for many-to-one
        (reverse) relations.
        """
        opts = MIZDjangoOptions()
        opts.factory = type("AudioFactory", (object,), {})
        opts.model = Audio
        m2o_rel = Bestand._meta.get_field("audio").remote_field
        m2m_rel = Audio._meta.get_field("band").remote_field
        rels = [m2o_rel, m2m_rel]
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=rels)):
            opts.add_related_factories()
        self.assertTrue(hasattr(opts.factory, "bestand"))
        related_fac = getattr(opts.factory, "bestand")
        self.assertEqual(related_fac.name, "audio")
        self.assertEqual(related_fac.accessor_name, "bestand_set")
        self.assertEqual(related_fac.related_model, Bestand)
        # Check that the M2M relation was ignored:
        self.assertFalse(hasattr(opts.factory, "band"))

    def test_add_related_factories_inherited_relation(self):
        """Assert that add_related_factories can handle inherited relations."""

        class Moon(models.Model):
            orbits = models.ForeignKey("Planet", related_name="moons", on_delete=models.CASCADE)

        class Planet(models.Model):
            pass

        class Earth(Planet):
            pass

        opts = MIZDjangoOptions()
        opts.factory = type("FirmFactory", (object,), {})
        opts.model = Earth
        rel = Moon._meta.get_field("orbits").remote_field
        with mock.patch("tests.model_factory.get_model_relations", Mock(return_value=[rel])):
            opts.add_related_factories()
        self.assertTrue(hasattr(opts.factory, "moons"))
        related_fac = getattr(opts.factory, "moons")
        self.assertEqual(related_fac.name, "orbits")
        self.assertEqual(related_fac.accessor_name, "moons")
        self.assertEqual(related_fac.related_model, Moon)

    def test_add_sub_factories_self_relations(self):
        """Assert that add_sub_factories handles self relations properly."""
        opts = MIZDjangoOptions()
        opts.factory = type("AncestorFactory", (object,), {})
        opts.model = Ancestor
        field = Ancestor._meta.get_field("ancestor")
        with mock.patch("tests.model_factory.get_model_fields", Mock(return_value=[field])):
            opts.add_sub_factories()
        self.assertTrue(hasattr(opts.factory, "ancestor"))
        self.assertIsInstance(getattr(opts.factory, "ancestor"), SelfFactory)

    def test_check_declarations(self):
        """
        Assert that the dynamically created sub- and related factories are
        added to the 'declarations' dictionary.
        """

        class ForwardRelated(models.Model):
            pass

        class ReverseRelated(models.Model):
            x = models.ForeignKey("TestModel", related_name="reverse_related", on_delete=models.CASCADE)

        class ForwardM2M(models.Model):
            pass

        class ReverseM2M(models.Model):
            x = models.ManyToManyField("TestModel", related_name="reverse_m2m")

        class TestModel(models.Model):
            required = models.CharField(max_length=100)
            not_required = models.CharField(max_length=100, blank=True)
            forward_related = models.ForeignKey("ForwardRelated", on_delete=models.CASCADE)
            forward_m2m = models.ManyToManyField("ForwardM2m")
            self_related = models.ForeignKey("self", related_name="own", on_delete=models.CASCADE)

        opts = MIZDjangoOptions()
        opts.factory = type("DummyFactory", (factory.django.DjangoModelFactory,), {})
        # factory.FactoryOptions doesn't seem to like it when the model is set
        # directly (opts.model = TestModel). So mock get_model_class to return
        # the test model.
        # Note that get_model_fields and get_model_relations are not being
        # faked in order to keep the test simple.
        with mock.patch.object(opts, "get_model_class", Mock(return_value=TestModel)):
            opts.contribute_to_class(opts.factory)
        self.assertIn("required", opts.declarations)
        self.assertIn("forward_related", opts.declarations)
        self.assertIn("reverse_related", opts.declarations)
        self.assertIn("forward_m2m", opts.declarations)
        self.assertIn("reverse_m2m", opts.declarations)
        self.assertIn("self_related", opts.declarations)
        self.assertNotIn("not_required", opts.declarations)


class ModelFactoryTestCase(MIZTestCase):
    factory_class = None

    def setUp(self):
        super().setUp()
        if self.factory_class is not None:
            self.factory_class.reset_sequence()


class TestMagazinFactory(ModelFactoryTestCase):
    factory_class = modelfactory_factory(_models.Magazin)

    def test_magazin_name_field(self):
        self.assertEqual(self.factory_class().magazin_name, "TestMagazin0")
        self.assertEqual(self.factory_class().magazin_name, "TestMagazin1")
        self.assertEqual(self.factory_class(__sequence=42).magazin_name, "TestMagazin42")

    def test_issn_field(self):
        m = self.factory_class()
        self.assertTrue(m.issn)
        self.assertTrue(issn.is_valid(m.issn))

        m = self.factory_class(issn="45010528")
        self.assertEqual(m.issn, "45010528")

    def test_get_or_create(self):
        expected = self.factory_class()
        self.assertEqual(self.factory_class(magazin_name=expected.magazin_name), expected)


class TestAusgabeFactory(ModelFactoryTestCase):
    factory_class = modelfactory_factory(_models.Ausgabe)

    def test_ausgabejahr(self):
        a = self.factory_class(ausgabejahr__jahr=2001)
        self.assertIn(2001, a.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertEqual(a.ausgabejahr_set.count(), 1)

        a = self.factory_class(ausgabejahr__jahr=[2001, 2002])
        self.assertIn(2001, a.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertIn(2002, a.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertEqual(a.ausgabejahr_set.count(), 2)

    def test_ausgabenum(self):
        a = self.factory_class(ausgabenum__num=21)
        self.assertIn(21, a.ausgabenum_set.values_list("num", flat=True))
        self.assertEqual(a.ausgabenum_set.count(), 1)

        a = self.factory_class(ausgabenum__num=[21, 22])
        self.assertIn(21, a.ausgabenum_set.values_list("num", flat=True))
        self.assertIn(22, a.ausgabenum_set.values_list("num", flat=True))
        self.assertEqual(a.ausgabenum_set.count(), 2)

    def test_ausgabelnum(self):
        a = self.factory_class(ausgabelnum__lnum=21)
        self.assertIn(21, a.ausgabelnum_set.values_list("lnum", flat=True))
        self.assertEqual(a.ausgabelnum_set.count(), 1)

        a = self.factory_class(ausgabelnum__lnum=[21, 22])
        self.assertIn(21, a.ausgabelnum_set.values_list("lnum", flat=True))
        self.assertIn(22, a.ausgabelnum_set.values_list("lnum", flat=True))
        self.assertEqual(a.ausgabelnum_set.count(), 2)

    def test_ausgabemonat(self):
        januar, _ = _models.Monat.objects.get_or_create(monat="Januar", abk="Jan", ordinal=1)
        februar, _ = _models.Monat.objects.get_or_create(monat="Februar", abk="Feb", ordinal=2)

        a = self.factory_class(ausgabemonat__monat__monat="Januar")
        self.assertIn((januar.pk, "Januar"), a.ausgabemonat_set.values_list("monat__id", "monat__monat"))
        self.assertEqual(a.ausgabemonat_set.count(), 1)

        a = self.factory_class(ausgabemonat__monat__ordinal=1)
        self.assertIn(
            (januar.pk, "Januar", 1), a.ausgabemonat_set.values_list("monat__id", "monat__monat", "monat__ordinal")
        )
        self.assertEqual(a.ausgabemonat_set.count(), 1)

        a = self.factory_class(ausgabemonat__monat__monat=["Januar", "Februar"])
        self.assertIn((januar.pk, "Januar"), a.ausgabemonat_set.values_list("monat__id", "monat__monat"))
        self.assertIn((februar.pk, "Februar"), a.ausgabemonat_set.values_list("monat__id", "monat__monat"))
        self.assertEqual(a.ausgabemonat_set.count(), 2)

        a = self.factory_class(ausgabemonat__monat__ordinal=[1, 2])
        self.assertIn(
            (januar.pk, "Januar", 1), a.ausgabemonat_set.values_list("monat__id", "monat__monat", "monat__ordinal")
        )
        self.assertIn(
            (februar.pk, "Februar", 2), a.ausgabemonat_set.values_list("monat__id", "monat__monat", "monat__ordinal")
        )
        self.assertEqual(a.ausgabemonat_set.count(), 2)

    def test_ausgabe_magazin(self):
        a = self.factory_class(magazin__magazin_name="Testmagazin")
        self.assertEqual(a.magazin.magazin_name, "Testmagazin")

    def test_complex_creation(self):
        lagerort_factory = modelfactory_factory(_models.Lagerort)
        lagerort_1 = lagerort_factory(ort="TestLagerOrt")
        lagerort_2 = lagerort_factory(ort="TestLagerOrt2")
        prov = modelfactory_factory(_models.Provenienz)(geber__name="TestCase")

        obj1 = self.factory_class(
            magazin__magazin_name="Testmagazin",
            ausgabejahr__jahr=2000,
            ausgabenum__num=1,
            bestand__lagerort=lagerort_1,
            bestand__provenienz=prov,
        )
        obj2 = self.factory_class(
            magazin__magazin_name="Testmagazin",
            ausgabejahr__jahr=2000,
            ausgabenum__num=2,
            bestand__lagerort=[lagerort_1, lagerort_2],
            bestand__provenienz=[None, prov],
        )
        obj3 = self.factory_class(
            magazin__magazin_name="Testmagazin",
            ausgabejahr__jahr=2000,
            ausgabenum__num=3,
            bestand__lagerort=lagerort_2,
        )

        self.assertEqual(obj1.magazin.magazin_name, "Testmagazin")
        self.assertIn(2000, obj1.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertIn(1, obj1.ausgabenum_set.values_list("num", flat=True))
        self.assertEqual(obj1.bestand_set.count(), 1)
        self.assertEqual(obj1.bestand_set.first().lagerort, lagerort_1)
        self.assertEqual(obj1.bestand_set.first().provenienz, prov)

        self.assertEqual(obj2.magazin.magazin_name, "Testmagazin")
        self.assertIn(2000, obj2.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertIn(2, obj2.ausgabenum_set.values_list("num", flat=True))
        self.assertEqual(obj2.bestand_set.count(), 2)
        b1, b2 = obj2.bestand_set.all()
        self.assertEqual(b1.lagerort, lagerort_1)
        self.assertIsNone(b1.provenienz)
        self.assertEqual(b2.lagerort, lagerort_2)
        self.assertEqual(b2.provenienz, prov)

        self.assertEqual(obj3.magazin.magazin_name, "Testmagazin")
        self.assertIn(2000, obj3.ausgabejahr_set.values_list("jahr", flat=True))
        self.assertIn(3, obj3.ausgabenum_set.values_list("num", flat=True))
        self.assertEqual(obj3.bestand_set.count(), 1)
        self.assertEqual(obj3.bestand_set.first().lagerort, lagerort_2)
        self.assertIsNone(obj3.bestand_set.first().provenienz)


class TestAutorFactory(ModelFactoryTestCase):
    factory_class = modelfactory_factory(_models.Autor)

    def test_kuerzel_field(self):
        """Assert that kuerzel depends on the Person's name."""
        a = self.factory_class()
        expected = a.person.vorname[0] + a.person.nachname[0]
        self.assertEqual(a.kuerzel, expected)

        a = self.factory_class(person__vorname="", person__nachname="Foo")
        self.assertEqual(a.kuerzel, "FO")

        a = self.factory_class(person=None)
        self.assertEqual(a.kuerzel, "XY")

        a = self.factory_class(kuerzel="AB")
        self.assertEqual(a.kuerzel, "AB")


class TestMonatFactory(ModelFactoryTestCase):
    factory_class = modelfactory_factory(_models.Monat)

    def test_abk_field(self):
        """Assert that abk depends on the monat's 'name'."""
        m = self.factory_class()
        self.assertEqual(m.abk, m.monat[:3])

        m = self.factory_class(monat="Nope")
        self.assertEqual(m.abk, "Nop")

    def test_get_or_create(self):
        expected = self.factory_class()
        self.assertEqual(self.factory_class(monat=expected.monat), expected)
