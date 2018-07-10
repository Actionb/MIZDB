from .base import *

from DBentry.factory import *

class TestRuntimeFactoryMixin(TestCase):

    local_factory_module = 'DBentry.factory'    # the module modelfactory_factory lives in
    base_factory_module = 'factory.base'
    
    # subclassing factory.SubFactory as the mixin's functionality should not depend on any custom classes for these tests
    dummy_factory = type('Dummy', (RuntimeFactoryMixin, factory.SubFactory), {})
    
    def test_existing_factory(self):
        # Assert that factory property returns the factory we're passing to __init__
        fac = self.dummy_factory(AutorFactory)
        self.assertEqual(AutorFactory, fac.factory)
        self.assertEqual(fac.factory.__module__,  self.local_factory_module)
        
    def test_new_factory(self):
        # Assert that the factory property can create a new factory if needed  
        fac = self.dummy_factory(self.local_factory_module + '.DoesNotExit', related_model = technik)
        self.assertEqual(fac.factory._meta.model, technik)
        from DBentry import factory
        self.assertIn('technik', factory._cache)
        
    def test_new_factory_wo_related_model(self):
        # factory property should raise an AttributeError if the factory's related_model attribute is None and a new factory has to be created.
        fac = self.dummy_factory(self.local_factory_module + 'beep', related_model = None)
        with self.assertRaises(AttributeError):
            fac.factory
            
class TestUniqueFaker(TestCase):
    
    def test_init(self):
        # UniqueFaker.function should default to lambda n: n
        faker = UniqueFaker('name', function = None)
        self.assertEqual(faker.function.__name__,  '<lambda>')
        self.assertEqual(faker.function(1), 1)
        self.assertEqual(faker.function(42), 42)
        
        # UniqueFaker should accept a provider's name as well as a factory.Faker instance
        faker = UniqueFaker('month')
        self.assertEqual(faker.faker.provider, 'month')
        
        faker = UniqueFaker(factory.Faker('month'), function = lambda n:n)
        self.assertEqual(faker.faker.provider, 'month')
        
class TestSelfFactory(TestCase):
    
    def test_evaluate(self):
        GenreFactory = modelfactory_factory(genre)
        created = GenreFactory(ober=None)
        self.assertIsNone(created.ober)
        
        created = GenreFactory(ober__ober__ober=None)
        self.assertIsNotNone(created.ober)
        self.assertIsNotNone(created.ober.ober)
        self.assertIsNone(created.ober.ober.ober)
        
        # Assert that SelfFactory creates exactly no related object when no params are given 
        # and does not get stuck in infinity recursion
        created = GenreFactory()
        self.assertIsNone(created.ober)
        
        # And now with actual data
        ober = GenreFactory(genre='Obergenre')
        sub = GenreFactory(genre='Subgenre', ober = ober)
        self.assertEqual(sub.ober, ober)
        self.assertIn(sub, ober.sub_genres.all())
        
        # Assert that SelfFactory creates one related object if it is required
        GenreFactory.ober.required = True
        created = GenreFactory()
        self.assertIsNotNone(created.ober)
        self.assertIsNone(created.ober.ober)
        GenreFactory.ober.required = False
            
class TestRelatedFactory(TestCase):
    
    def test_rf_string_direct(self):
        g = make(genre, genre = 'TestGenre0', genre_alias__alias = 'Alias1')
        self.assertIn('Alias1', g.genre_alias_set.values_list('alias',flat=True))
    
    def test_rf_string_single_list(self):    
        g = make(genre, genre = 'TestGenre0', genre_alias__alias = ['Alias1'])
        self.assertIn('Alias1', g.genre_alias_set.values_list('alias', flat = True))
        
    def test_rf_string_list(self):
        g = make(genre, genre = 'TestGenre0', genre_alias__alias = ['Alias1', 'Alias2'])
        self.assertIn('Alias1', g.genre_alias_set.values_list('alias', flat = True))
        
    def test_rf_instance_direct(self):
        m1 = make(musiker)
        p = make(person, vorname = 'Alice', nachname = 'Testman', musiker = m1)
        self.assertIn(m1, p.musiker_set.all())
        
    def test_rf_instance_single_list(self):
        m1 = make(musiker)
        p = make(person, vorname = 'Alice', nachname = 'Testman', musiker = [m1])
        self.assertIn(m1, p.musiker_set.all())
        
    def test_rf_instance_list(self):
        m1 = make(musiker)
        m2 = make(musiker)
        p = make(person, vorname = 'Alice', nachname = 'Testman', musiker = [m1, m2])
        self.assertIn(m1, p.musiker_set.all())
        self.assertIn(m2, p.musiker_set.all())
        
    def test_rf_extra(self):
        g = make(genre, genre = 'TestGenre0', genre_alias__extra = 3)
        self.assertEqual(g.genre_alias_set.count(), 3)
    
class TestM2MFactory(TestCase):
    
    def test_m2m_string_direct(self):
        m = make(musiker, genre__genre='TestGenre1')
        self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
    
    def test_m2m_string_single_list(self):
        m = make(musiker, genre__genre=['TestGenre1'])
        self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
    
    def test_m2m_string_list(self):
        m = make(musiker, genre__genre=['TestGenre1', 'TestGenre2'])
        self.assertIn('TestGenre1', m.genre.values_list('genre', flat=True))
        self.assertIn('TestGenre2', m.genre.values_list('genre', flat=True))
    
    def test_m2m_instance_direct(self):
        g1 = make(genre)
        m = make(musiker, genre=g1)
        self.assertIn(g1, m.genre.all())
    
    def test_m2m_instance_single_list(self):
        g1 = make(genre)
        m = make(musiker, genre=[g1])
        self.assertIn(g1, m.genre.all())
    
    def test_m2m_instance_list(self):
        g1 = make(genre)
        g2 = make(genre)
        m = make(musiker, genre=[g1, g2])
        self.assertIn(g1, m.genre.all())
        self.assertIn(g2, m.genre.all())
        
    def test_m2m_extra(self):
        m = make(musiker, genre__extra=3)
        self.assertEqual(m.genre.count(), 3)
        
        g1 = make(genre)
        g2 = make(genre)
        m = make(musiker, genre=[g1, g2], genre__extra=2)
        self.assertIn(g1, m.genre.all())
        self.assertIn(g2, m.genre.all())
        self.assertEqual(m.genre.count(), 4)
        
    def test_m2m_pops_accessor_name(self):
        m2m = M2MFactory('DBentry.factory.whatever', accessor_name = 'beep boop', related_model = genre)
        self.assertIsNone(m2m.accessor_name)

class TestMIZDjangoOptions(TestCase):
    
    def test_get_decl_for_model_field(self):
        # Assert that the dynamically added 'base' fields have the correct types
        func = MIZDjangoOptions._get_decl_for_model_field
        # CharField / TextField => factory.Faker('word')  || UniqueFaker('word')  if unique
        decl = func(audio._meta.get_field('quelle'))
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, 'word')
        
        decl = func(land._meta.get_field('land_name'))
        self.assertIsInstance(decl, UniqueFaker)
        self.assertEqual(decl.faker.provider, 'word')
        
        # IntegerField / DurationField => factory.Faker('pyint') || factory.Sequence(lambda n: n)  if unique
        decl = func(ausgabe._meta.get_field('jahrgang'))
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, 'pyint')
        
        mock_field = Mock(unique = True, get_internal_type = mockv('IntegerField'))
        decl = func(mock_field)
        self.assertIsInstance(decl, factory.Sequence)
        
        decl = func(audio._meta.get_field('laufzeit')) # DurationField
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, 'pyint')
        
        # BooleanField =>  factory.Faker('pybool')
        decl = func(ausgabe._meta.get_field('sonderausgabe'))
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, 'pybool')
        
        # DateField => factory.Faker('date')
        decl = func(ausgabe._meta.get_field('e_datum'))
        self.assertIsInstance(decl, factory.Faker)
        self.assertEqual(decl.provider, 'date')
    
    def test_adds_required_fields(self):
        # A dynamically created factory *must* include model fields that are required
        # veranstaltung has three required fields: name (CharField), datum (DateField), spielort (ForeignKey(spielort))
        fac = modelfactory_factory(veranstaltung)
        self.assertIn('name', dir(fac))
        self.assertIn('datum', dir(fac))
        self.assertIn('spielort', dir(fac))
        
    def test_accounts_for_unique_constraints(self):
        # MIZDjangoOptions should make sure that declarations (base or SubFactory) return unique values if the model field is unique
        pass
        
    def test_add_m2m_factories(self):
        # Assert that the created m2m factories are following the relation correctly
        fac = modelfactory_factory(artikel)
        self.assertEqual(fac.genre.factory._meta.model, genre)
        self.assertEqual(fac.schlagwort.factory._meta.model, schlagwort)
        self.assertEqual(fac.person.factory._meta.model, person)
        self.assertEqual(fac.autor.factory._meta.model, autor)
        self.assertEqual(fac.band.factory._meta.model, band)
        self.assertEqual(fac.musiker.factory._meta.model, musiker)
        self.assertEqual(fac.ort.factory._meta.model, ort)
        self.assertEqual(fac.spielort.factory._meta.model, spielort)
        self.assertEqual(fac.veranstaltung.factory._meta.model, veranstaltung)
        
        fac = modelfactory_factory(musiker)
        self.assertEqual(fac.audio.factory._meta.model, audio)
        self.assertEqual(fac.orte.factory._meta.model, ort)
        self.assertEqual(fac.artikel.factory._meta.model, artikel)
        self.assertEqual(fac.memorabilien.factory._meta.model, memorabilien)
        self.assertEqual(fac.datei.factory._meta.model, datei)
        self.assertEqual(fac.technik.factory._meta.model, technik)
        self.assertEqual(fac.bildmaterial.factory._meta.model, bildmaterial)
        self.assertEqual(fac.video.factory._meta.model, video)
        self.assertEqual(fac.dokument.factory._meta.model, dokument)
        self.assertEqual(fac.veranstaltung.factory._meta.model, veranstaltung)
        self.assertEqual(fac.genre.factory._meta.model, genre)
        self.assertEqual(fac.buch.factory._meta.model, buch)
        self.assertEqual(fac.instrument.factory._meta.model, instrument)
        self.assertEqual(fac.band.factory._meta.model, band)
        
    def test_add_related_factories(self):
        # Assert that the created related factories are following the relation correctly
        fac = modelfactory_factory(buch)
        self.assertEqual(fac.schriftenreihe.factory._meta.model, schriftenreihe)
        self.assertEqual(fac.buchband.factory._meta.model, buch)
        self.assertEqual(fac.verlag.factory._meta.model, verlag)
        self.assertEqual(fac.sprache.factory._meta.model, sprache)
        
    def test_add_sub_factories(self):
        # Assert that self relations are recognized properly
        fac = modelfactory_factory(buch)
        self.assertIsInstance(fac.buchband, SelfFactory)
        
    def test_check_declarations(self):
        # Assert that all dynamically created factories are accounted for in the correct declaration sets
        fac = modelfactory_factory(video)
        declarations = fac._meta.declarations
        # required base fields
        for field in get_model_fields(video, foreign = False, m2m = False):
            if field.has_default() or field.blank:
                continue
            self.assertIn(field.name, declarations, msg = '{} not found in base declarations'.format(field.name))
        self.assertIn('titel', declarations)
        self.assertIn('tracks', declarations)
        self.assertIn('laufzeit', declarations)
        
        # SubFactories
        for field in get_model_fields(video, base = False, foreign = True, m2m = False):
            self.assertIn(field.name, declarations, msg = '{} not found in SubFactory declarations'.format(field.name))
        self.assertIn('sender', declarations)
        
        # RelatedFactories
        for rel in get_model_relations(video, forward = False):
            if rel.many_to_many:
                continue
            name = rel.name
            self.assertIn(name, declarations, msg = '{} not found in reverse related declarations'.format(name))
        self.assertIn('bestand', declarations)
        self.assertIn('m2m_datei_quelle', declarations)
        
        # M2MFactories
        for rel in get_model_relations(video):
            if not rel.many_to_many:
                continue
            if rel.field.model == video:
                name = rel.field.name
            else:
                name = rel.name
            self.assertIn(name, declarations, msg = '{} not found in M2MFactory declarations'.format(name))
        self.assertIn('genre', declarations)
        self.assertIn('musiker', declarations)
        self.assertIn('schlagwort', declarations)
        self.assertIn('spielort', declarations)
        self.assertIn('person', declarations)
        self.assertIn('band', declarations)
        self.assertIn('veranstaltung', declarations)
    
class TestModelFactoryFactory(TestCase):
    
    def test_meta_kwargs(self):
        # Assert that the correct options class is created for the model factory
        pass

class ModelFactoryTestCase(TestCase):
    
    factory_class = None
    
    def setUp(self):
        # reset sequences
        if self.factory_class is not None:
            self.factory_class.reset_sequence()
        
class TestMagazinFactory(ModelFactoryTestCase):
    
    factory_class = modelfactory_factory(magazin)
    
    def test_magazin_name_field(self):
        self.assertEqual(self.factory_class().magazin_name, 'TestMagazin0')
        self.assertEqual(self.factory_class().magazin_name, 'TestMagazin1')
        self.assertEqual(self.factory_class(__sequence = 42).magazin_name, 'TestMagazin42')
        
    def test_issn_field(self):
        from stdnum import issn
        m = MagazinFactory()
        self.assertTrue(m.issn)
        self.assertTrue(issn.is_valid(m.issn))
        
        m = MagazinFactory(issn = '45010528')
        self.assertEqual(m.issn, '4501-0528')
        
    def test_get_or_create(self):
        expected = self.factory_class()
        self.assertEqual(self.factory_class(magazin_name=expected.magazin_name), expected)
        
        
class TestAusgabeFactory(ModelFactoryTestCase):
    
    factory_class = modelfactory_factory(ausgabe)
    
    def test_ausgabe_jahr(self):
        a = self.factory_class(ausgabe_jahr__jahr=2001)
        self.assertIn(2001, a.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertEqual(a.ausgabe_jahr_set.count(), 1)
        
        a = self.factory_class(ausgabe_jahr__jahr=[2001, 2002])
        self.assertIn(2001, a.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertIn(2002, a.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertEqual(a.ausgabe_jahr_set.count(), 2)
        
    def test_ausgabe_num(self):
        a = self.factory_class(ausgabe_num__num=21)
        self.assertIn(21, a.ausgabe_num_set.values_list('num', flat=True))
        self.assertEqual(a.ausgabe_num_set.count(), 1)
        
        a = self.factory_class(ausgabe_num__num=[21, 22])
        self.assertIn(21, a.ausgabe_num_set.values_list('num', flat=True))
        self.assertIn(22, a.ausgabe_num_set.values_list('num', flat=True))
        self.assertEqual(a.ausgabe_num_set.count(), 2)
        
    def test_ausgabe_lnum(self):
        a = self.factory_class(ausgabe_lnum__lnum=21)
        self.assertIn(21, a.ausgabe_lnum_set.values_list('lnum', flat=True))
        self.assertEqual(a.ausgabe_lnum_set.count(), 1)
        
        a = self.factory_class(ausgabe_lnum__lnum=[21, 22])
        self.assertIn(21, a.ausgabe_lnum_set.values_list('lnum', flat=True))
        self.assertIn(22, a.ausgabe_lnum_set.values_list('lnum', flat=True))
        self.assertEqual(a.ausgabe_lnum_set.count(), 2)
        
    def ausgabe_monat(self):
        a = self.factory_class(ausgabe_monat__monat__monat='Januar')
        self.assertIn('Januar', a.ausgabe_monat_set.values_list('monat__monat', flat=True))
        self.assertEqual(a.ausgabe_monat_set.count(), 1)
        
        a = self.factory_class(ausgabe_monat__monat__monat=['Januar', 'Februar'])
        self.assertIn('Januar', a.ausgabe_monat_set.values_list('monat__monat', flat=True))
        self.assertIn('Februar', a.ausgabe_monat_set.values_list('monat__monat', flat=True))
        self.assertEqual(a.ausgabe_monat_set.count(), 2)
        
    def test_ausgabe_magazin(self):
        a = self.factory_class(magazin__magazin_name='Testmagazin')
        self.assertEqual(a.magazin.magazin_name, 'Testmagazin')
        
    def test_complex_creation(self):
        lagerort_factory = modelfactory_factory(lagerort)
        lagerort_1 = lagerort_factory(ort='TestLagerOrt')
        lagerort_2 = lagerort_factory(ort='TestLagerOrt2')
        prov = modelfactory_factory(provenienz)(geber__name='TestCase')
        
        obj1 = self.factory_class(
                magazin__magazin_name = 'Testmagazin', 
                ausgabe_jahr__jahr = 2000, ausgabe_num__num = 1, 
                bestand__lagerort = lagerort_1, bestand__provenienz = prov 
            )
        obj2 = self.factory_class(
                magazin__magazin_name = 'Testmagazin', 
                ausgabe_jahr__jahr = 2000, ausgabe_num__num = 2, 
                bestand__lagerort = [lagerort_1, lagerort_2], 
                bestand__provenienz = [None, prov], 
            )
        obj3 = self.factory_class(
                magazin__magazin_name = 'Testmagazin', 
                ausgabe_jahr__jahr = 2000, ausgabe_num__num = 3, 
                bestand__lagerort = lagerort_2, 
            )
        
        self.assertEqual(obj1.magazin.magazin_name, 'Testmagazin')
        self.assertIn(2000, obj1.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertIn(1, obj1.ausgabe_num_set.values_list('num', flat=True))
        self.assertEqual(obj1.bestand_set.count(), 1)
        self.assertEqual(obj1.bestand_set.first().lagerort, lagerort_1)
        self.assertEqual(obj1.bestand_set.first().provenienz, prov)
        
        self.assertEqual(obj2.magazin.magazin_name, 'Testmagazin')
        self.assertIn(2000, obj2.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertIn(2, obj2.ausgabe_num_set.values_list('num', flat=True))
        self.assertEqual(obj2.bestand_set.count(), 2)
        b1, b2 = obj2.bestand_set.all()
        self.assertEqual(b1.lagerort, lagerort_1)
        self.assertIsNone(b1.provenienz)
        self.assertEqual(b2.lagerort, lagerort_2)
        self.assertEqual(b2.provenienz, prov)
        
        self.assertEqual(obj3.magazin.magazin_name, 'Testmagazin')
        self.assertIn(2000, obj3.ausgabe_jahr_set.values_list('jahr', flat=True))
        self.assertIn(3, obj3.ausgabe_num_set.values_list('num', flat=True))
        self.assertEqual(obj3.bestand_set.count(), 1)
        self.assertEqual(obj3.bestand_set.first().lagerort, lagerort_2)
        self.assertIsNone(obj3.bestand_set.first().provenienz)
        
class TestAutorFactory(ModelFactoryTestCase):
    
    factory_class = modelfactory_factory(autor)
    
    def test_kuerzel_field(self):
        # Assert that kuerzel depends on the person's name
        a = self.factory_class()
        expected = a.person.vorname[0] + a.person.nachname[0]
        self.assertEqual(a.kuerzel, expected)
        
        a = self.factory_class(person__vorname='', person__nachname='Foo')
        self.assertEqual(a.kuerzel, 'FO')
        
        a = self.factory_class(person=None)
        self.assertEqual(a.kuerzel, 'XY')
        
        a = self.factory_class(kuerzel = 'AB')
        self.assertEqual(a.kuerzel, 'AB')
        
class TestMonatFactory(ModelFactoryTestCase):
    
    factory_class = modelfactory_factory(monat)
    
    def test_abk_field(self):
        # Assert that abk depends on the monat's 'name'
        m = self.factory_class()
        self.assertEqual(m.abk, m.monat[:3])
        
        m = self.factory_class(monat = 'Nope')
        self.assertEqual(m.abk, 'Nop')
        
    def test_get_or_create(self):
        expected = self.factory_class()
        self.assertEqual(self.factory_class(monat=expected.monat), expected)
